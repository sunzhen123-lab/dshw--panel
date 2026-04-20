# -*- coding: utf-8 -*-
"""
从 AkShare / 东方财富拉取 A 股年报三大表与行业、ST、宏观 M2（非模拟）。
原始表写入 ``data/raw/``（与课程作业路径一致）。
环境变量 ``P03_MAX_STOCKS``：下载股票数上限（默认 100）。
"""
import os
import time
import warnings
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from codes.paths import RAW, ROOT  # noqa: E402

MARKER = RAW / ".download_complete"


def _em_symbol(code: str) -> str:
    c = str(code).strip().zfill(6)
    return ("SH" if c.startswith("6") else "SZ") + c


def _universe() -> pd.DataFrame:
    import akshare as ak

    base = ak.stock_info_a_code_name()
    base = base.rename(columns={"code": "stkcd", "name": "sec_name"})
    base["stkcd"] = base["stkcd"].astype(str).str.zfill(6)
    m = (
        base["stkcd"].str.match(r"^(00|30|60|68)\d{4}$")
        & ~base["sec_name"].str.contains(r"ST|\*ST", regex=True, na=False)
    )
    base = base.loc[m].copy()
    return base.reset_index(drop=True)


def _st_codes() -> set:
    import akshare as ak

    try:
        st = ak.stock_zh_a_st_em()
        return set(st["代码"].astype(str).str.zfill(6))
    except Exception:
        return set()


def _fetch_three_tables(symbol: str):
    import akshare as ak

    try:
        bs = ak.stock_balance_sheet_by_yearly_em(symbol=symbol)
        time.sleep(0.12)
        inc = ak.stock_profit_sheet_by_yearly_em(symbol=symbol)
        time.sleep(0.12)
        cf = ak.stock_cash_flow_sheet_by_yearly_em(symbol=symbol)
        time.sleep(0.12)
        return bs, inc, cf
    except Exception:
        return None, None, None


def _pick_cols(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    out = {}
    for std, col in mapping.items():
        if col in df.columns:
            out[std] = df[col]
        else:
            out[std] = np.nan
    return pd.DataFrame(out)


def _standardize_balance(bs: pd.DataFrame, stkcd: str) -> pd.DataFrame:
    if bs is None or bs.empty:
        return pd.DataFrame()
    df = bs.copy()
    df["stkcd"] = stkcd
    df["report_date"] = pd.to_datetime(df["REPORT_DATE"], errors="coerce")
    df["year"] = df["report_date"].dt.year
    if "REPORT_TYPE" in df.columns:
        df = df[df["REPORT_TYPE"].astype(str).str.contains("年报")].copy()
    cols = {
        "total_assets": "TOTAL_ASSETS",
        "total_liabilities": "TOTAL_LIABILITIES",
        "fixed_assets": "FIXED_ASSET",
        "total_current_assets": "TOTAL_CURRENT_ASSETS",
        "total_current_liab": "TOTAL_CURRENT_LIAB",
    }
    part = _pick_cols(df, {k: v for k, v in cols.items()})
    part["stkcd"] = stkcd
    part["year"] = df["year"].values
    part["report_date"] = df["report_date"].values
    return part.dropna(subset=["year"])


def _standardize_income(inc: pd.DataFrame, stkcd: str) -> pd.DataFrame:
    if inc is None or inc.empty:
        return pd.DataFrame()
    df = inc.copy()
    df["report_date"] = pd.to_datetime(df["REPORT_DATE"], errors="coerce")
    df["year"] = df["report_date"].dt.year
    if "REPORT_TYPE" in df.columns:
        df = df[df["REPORT_TYPE"].astype(str).str.contains("年报")].copy()
    part = _pick_cols(df, {"net_profit": "PARENT_NETPROFIT"})
    part["stkcd"] = stkcd
    part["year"] = df["year"].values
    return part.dropna(subset=["year"])


def _standardize_cf(cf: pd.DataFrame, stkcd: str) -> pd.DataFrame:
    if cf is None or cf.empty:
        return pd.DataFrame()
    df = cf.copy()
    df["report_date"] = pd.to_datetime(df["REPORT_DATE"], errors="coerce")
    df["year"] = df["report_date"].dt.year
    if "REPORT_TYPE" in df.columns:
        df = df[df["REPORT_TYPE"].astype(str).str.contains("年报")].copy()
    dep_cols = [
        "FA_IR_DEPR",
        "OILGAS_BIOLOGY_DEPR",
        "IR_DEPR",
        "IA_AMORTIZE",
        "LPE_AMORTIZE",
        "DEFER_INCOME_AMORTIZE",
        "USERIGHT_ASSET_AMORTIZE",
    ]
    dep = pd.Series(0.0, index=df.index)
    for c in dep_cols:
        if c in df.columns:
            dep = dep + pd.to_numeric(df[c], errors="coerce").fillna(0)
    out = pd.DataFrame({"stkcd": stkcd, "year": df["year"].values, "dep_amort": dep.values})
    return out.dropna(subset=["year"])


def _industry_row(stkcd: str) -> dict:
    import akshare as ak

    try:
        d = ak.stock_industry_change_cninfo(
            symbol=stkcd, start_date="20100101", end_date="20261231"
        )
        time.sleep(0.08)
        if d is None or d.empty:
            return {"stkcd": stkcd, "ind_gate": "", "ind_mid": "", "ind_code_em": ""}
        d = d.sort_values("变更日期")
        last = d.iloc[-1]
        return {
            "stkcd": stkcd,
            "ind_gate": str(last.get("行业门类", "") or ""),
            "ind_mid": str(last.get("行业中类", "") or ""),
            "ind_code_em": str(last.get("行业编码", "") or ""),
        }
    except Exception:
        return {"stkcd": stkcd, "ind_gate": "", "ind_mid": "", "ind_code_em": ""}


def _soe_from_profile(stkcd: str) -> int:
    import akshare as ak

    try:
        prof = ak.stock_profile_cninfo(symbol=stkcd)
        time.sleep(0.08)
        if prof is None or prof.empty:
            return 0
        intro = ""
        if "机构简介" in prof.columns:
            intro = str(prof.iloc[0].get("机构简介", "") or "")
        if "经营范围" in prof.columns:
            intro += str(prof.iloc[0].get("经营范围", "") or "")
        keys = ("国有", "国资委", "财政部", "汇金", "国资", "国有独资", "国有控股")
        return 1 if any(k in intro for k in keys) else 0
    except Exception:
        return 0


def download_raw(max_stocks: Optional[int] = None, force: bool = False) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    if MARKER.exists() and not force:
        print(
            "[fetch] data/raw 已存在，跳过下载。使用 --download 或删除 data/raw/.download_complete 可重新拉取。"
        )
        return

    import akshare as ak

    mx = max_stocks or int(os.environ.get("P03_MAX_STOCKS", "100"))
    uni = _universe()
    st_set = _st_codes()
    uni = uni[~uni["stkcd"].isin(st_set)].head(mx)

    bal_parts, inc_parts, cf_parts, ind_rows = [], [], [], []
    ok, fail = 0, 0
    for _, row in uni.iterrows():
        stk = row["stkcd"]
        sym = _em_symbol(stk)
        bs, inc, cf = _fetch_three_tables(sym)
        if bs is None:
            fail += 1
            continue
        b = _standardize_balance(bs, stk)
        p = _standardize_income(inc, stk)
        c = _standardize_cf(cf, stk)
        if b.empty:
            fail += 1
            continue
        bal_parts.append(b)
        if not p.empty:
            inc_parts.append(p)
        if not c.empty:
            cf_parts.append(c)
        ind_rows.append(_industry_row(stk))
        ok += 1
        if (ok + fail) % 20 == 0:
            print(f"  ... 已请求 {ok + fail} 只，成功 {ok}，失败 {fail}")

    if not bal_parts:
        raise RuntimeError("未能下载任何资产负债表数据，请检查网络或稍后重试。")

    balance = pd.concat(bal_parts, ignore_index=True)
    income = pd.concat(inc_parts, ignore_index=True) if inc_parts else pd.DataFrame()
    cashflow = pd.concat(cf_parts, ignore_index=True) if cf_parts else pd.DataFrame()
    industry = pd.DataFrame(ind_rows)

    soe_list = []
    for stk in industry["stkcd"].unique():
        soe_list.append({"stkcd": stk, "soe": _soe_from_profile(stk)})
        if len(soe_list) % 25 == 0:
            print(f"  ... SOE 解析 {len(soe_list)}/{len(industry['stkcd'].unique())}")
    ownership = pd.DataFrame(soe_list)

    m2m = ak.macro_china_money_supply()
    m2m["year"] = m2m["月份"].astype(str).str[:4].astype(int)
    m2m["m2"] = pd.to_numeric(m2m["货币和准货币(M2)-数量(亿元)"], errors="coerce")
    yend = m2m.sort_values("月份").groupby("year", as_index=False).tail(1)
    yend = yend[["year", "m2"]].sort_values("year")
    yend["m2_growth"] = yend["m2"].pct_change() * 100.0
    m2_out = yend[(yend["year"] >= 2010) & (yend["year"] <= 2025)].copy()

    balance.to_csv(RAW / "balance_sheet.csv", index=False, encoding="utf-8-sig")
    income.to_csv(RAW / "income_stmt.csv", index=False, encoding="utf-8-sig")
    cashflow.to_csv(RAW / "cashflow.csv", index=False, encoding="utf-8-sig")
    ownership.to_csv(RAW / "ownership.csv", index=False, encoding="utf-8-sig")
    industry.to_csv(RAW / "industry.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"stkcd": sorted(st_set)}).to_csv(RAW / "st_flag.csv", index=False, encoding="utf-8-sig")
    m2_out.to_csv(RAW / "m2.csv", index=False, encoding="utf-8-sig")

    MARKER.write_text(f"ok stocks={ok} fail={fail} max={mx}\n", encoding="utf-8")
    print(f"[fetch] 完成：成功 {ok}，失败 {fail}，原始表已写入 {RAW}")
