# -*- coding: utf-8 -*-
"""
合并 ``data/raw/``、构造变量（与作业符号一致）、按 ex_P03 §1.3 顺序筛选、
截面（按年）1% Winsorize（$Lev,NPR,Tang,Growth,NDTS$；选做 $Liq$）。
"""
from pathlib import Path

import numpy as np
import pandas as pd

from codes.paths import CLEAN, RAW  # noqa: E402


def _winsorize_year(df: pd.DataFrame, col: str, year_col: str = "year", p: float = 0.01):
    def clip(g):
        lo = g.quantile(p)
        hi = g.quantile(1 - p)
        return g.clip(lo, hi)

    return df.groupby(year_col)[col].transform(clip)


def _flow_row(step: str, n_drop, n_obs: int, n_firm: int) -> dict:
    if n_drop is None or (isinstance(n_drop, float) and np.isnan(n_drop)):
        dr = "—"
    else:
        dr = int(n_drop)
    return {
        "筛选步骤": step,
        "剔除观测数": dr,
        "剩余观测数": int(n_obs),
        "剩余公司数": int(n_firm),
    }


def build_panel() -> pd.DataFrame:
    bal = pd.read_csv(RAW / "balance_sheet.csv")
    keep_b = [
        c
        for c in [
            "stkcd",
            "year",
            "total_assets",
            "total_liabilities",
            "fixed_assets",
            "total_current_assets",
            "total_current_liab",
        ]
        if c in bal.columns
    ]
    bal = bal[keep_b].copy()
    inc = pd.read_csv(RAW / "income_stmt.csv")
    cf = pd.read_csv(RAW / "cashflow.csv")
    own = pd.read_csv(RAW / "ownership.csv")
    ind = pd.read_csv(RAW / "industry.csv")
    m2 = pd.read_csv(RAW / "m2.csv")
    stf = pd.read_csv(RAW / "st_flag.csv")
    st_codes = set(stf["stkcd"].astype(str).str.zfill(6))

    bal["stkcd"] = bal["stkcd"].astype(str).str.zfill(6)
    inc["stkcd"] = inc["stkcd"].astype(str).str.zfill(6)
    cf["stkcd"] = cf["stkcd"].astype(str).str.zfill(6)
    own["stkcd"] = own["stkcd"].astype(str).str.zfill(6)
    ind["stkcd"] = ind["stkcd"].astype(str).str.zfill(6)

    inc2 = inc[["stkcd", "year", "net_profit"]].copy()
    cf2 = cf[["stkcd", "year", "dep_amort"]].copy()
    df = bal.merge(inc2, on=["stkcd", "year"], how="left")
    df = df.merge(cf2, on=["stkcd", "year"], how="left")
    df = df.merge(own, on="stkcd", how="left")
    df = df.merge(ind, on="stkcd", how="left")
    df = df.merge(m2[["year", "m2", "m2_growth"]], on="year", how="left")

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    df = df[(df["year"] >= 2010) & (df["year"] <= 2025)].copy()

    flow = []
    n0, c0 = len(df), df["stkcd"].nunique()
    flow.append(_flow_row("初始样本（2010–2025，合并年报后）", np.nan, n0, c0))

    gate_fin = df["ind_gate"].astype(str).str.contains("金融|保险", na=False)
    code_j = df["ind_code_em"].astype(str).str.upper().str.startswith("J")
    d1 = df[~(gate_fin | code_j)].copy()
    flow.append(
        _flow_row(
            "剔除金融、保险行业（证监会 J / 门类名含金融、保险）",
            n0 - len(d1),
            len(d1),
            d1["stkcd"].nunique(),
        )
    )

    d2 = d1[~d1["stkcd"].isin(st_codes)].copy()
    flow.append(
        _flow_row(
            "剔除 ST/PT 相关公司（当前风险警示名单近似；曾 ST 全历史需 CSMAR）",
            len(d1) - len(d2),
            len(d2),
            d2["stkcd"].nunique(),
        )
    )

    ta = pd.to_numeric(d2["total_assets"], errors="coerce")
    tl = pd.to_numeric(d2["total_liabilities"], errors="coerce")
    npf = pd.to_numeric(d2["net_profit"], errors="coerce")
    fa = pd.to_numeric(d2["fixed_assets"], errors="coerce")
    ca = pd.to_numeric(d2["total_current_assets"], errors="coerce")
    cl = pd.to_numeric(d2["total_current_liab"], errors="coerce")
    dep = pd.to_numeric(d2["dep_amort"], errors="coerce")

    d2["lev"] = tl / ta
    d2["npr"] = npf / ta
    d2["size"] = np.log(ta.clip(lower=1))
    d2["tang"] = fa / ta
    d2["ndts"] = dep / ta
    d2["liq"] = ca / cl.replace(0, np.nan)
    d2["soe"] = pd.to_numeric(d2["soe"], errors="coerce").fillna(0).astype(int)

    d2 = d2.sort_values(["stkcd", "year"])
    lag_ta = d2.groupby("stkcd")["total_assets"].shift(1)
    d2["growth"] = (ta - lag_ta) / lag_ta.replace(0, np.nan)

    d3 = d2[d2["lev"] <= 1].copy()
    flow.append(
        _flow_row(
            "剔除资不抵债（$Lev>1$）",
            len(d2) - len(d3),
            len(d3),
            d3["stkcd"].nunique(),
        )
    )

    need = ["lev", "npr", "size", "tang", "growth", "ndts", "soe"]
    d4 = d3.dropna(subset=need).copy()
    flow.append(
        _flow_row(
            "剔除关键变量缺失",
            len(d3) - len(d4),
            len(d4),
            d4["stkcd"].nunique(),
        )
    )

    def build_ind_code(r):
        gate = str(r.get("ind_gate", "") or "")
        mid = str(r.get("ind_mid", "") or "")
        if "制造" in gate or "制造业" in gate:
            s = mid[:3] if len(mid) >= 2 else mid
            return s or "C_other"
        return (gate[:1] + "_sec") if gate else "UNK"

    d4["ind_code"] = d4.apply(build_ind_code, axis=1)
    cnt = d4.groupby(["year", "ind_code"]).size().reset_index(name="n")
    small = set(cnt.loc[cnt["n"] < 30, "ind_code"])
    d4["ind_code"] = np.where(d4["ind_code"].isin(small), "CM_other", d4["ind_code"])

    winsor_cols = ["lev", "npr", "tang", "growth", "ndts"]
    if d4["liq"].notna().sum() > 10:
        winsor_cols.append("liq")
    for c in winsor_cols:
        d4[c + "_raw"] = d4[c]
    for c in winsor_cols:
        d4[c] = _winsorize_year(d4, c, "year", 0.01)

    flow.append(
        _flow_row(
            "**最终样本**",
            np.nan,
            len(d4),
            d4["stkcd"].nunique(),
        )
    )

    CLEAN.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(flow).to_csv(CLEAN / "sample_flow.csv", index=False, encoding="utf-8-sig")
    d4.to_csv(CLEAN / "panel_final.csv", index=False, encoding="utf-8-sig")
    print(f"[panel] 最终样本 {len(d4)} 观测，{d4['stkcd'].nunique()} 家公司")
    return d4
