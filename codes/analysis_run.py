# -*- coding: utf-8 -*-
"""
描述统计、相关系数（5% 显著性）、PanelOLS（``linearmodels``）与 Fig1–Fig7。

- **M1** TWFE：$Lev_{it}=\\alpha_i+\\lambda_t+\\beta NPR_{it}+\\gamma'X_{it}+\\varepsilon_{it}$，
  标准误按 **公司与年度双向聚类**（对齐 Stata ``vce(cluster stkcd year)`` 思路）。
- **M1′**：以 TWFE + $m2\\_growth_t$ 近似可观测宏观控制；完整 IFE 需 ``regife``（Stata）或专用 Python 包。
- **M4**：$Lev_{it}=\\alpha_i+\\lambda_t+\\beta_t NPR_{it}+\\cdots$ 以 ``npr + npr:C(year)`` 估计时变斜率并绘制 $\\hat{\\beta}_t$。
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from linearmodels.panel import PanelOLS
from scipy import stats

from codes.paths import FIG, ROOT, TAB  # noqa: E402
from codes.plot_font import apply_cn, fp, heatmap_annot_kw, legend_cn  # noqa: E402

FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)


def _indexed(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["stkcd"] = d["stkcd"].astype(str).str.zfill(6)
    d["year"] = d["year"].astype(int)
    d = d.set_index(["stkcd", "year"])
    d["year"] = d.index.get_level_values(1).astype(int)
    return d


def _cluster_two_way(data: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        index=data.index,
        data={
            "clu_entity": data.index.get_level_values(0).astype(str),
            "clu_time": data.index.get_level_values(1).astype(int),
        },
    )


def _twfe(
    formula: str,
    df: pd.DataFrame,
    *,
    min_rows: int = 30,
    min_entities: int = 4,
    twoway_cluster: bool = True,
):
    if df is None or len(df) < min_rows or df["stkcd"].nunique() < min_entities:
        return None
    data = _indexed(df)
    mod = PanelOLS.from_formula(
        formula,
        data=data,
        check_rank=False,
        drop_absorbed=True,
    )
    if twoway_cluster and len(df["year"].unique()) > 1:
        cl = _cluster_two_way(data)
        return mod.fit(cov_type="clustered", clusters=cl)
    return mod.fit(cov_type="clustered", cluster_entity=True)


def _save_summary(name: str, res) -> None:
    p = FIG.parent / f"reg_{name}.txt"
    if res is None:
        with open(p, "w", encoding="utf-8") as f:
            f.write("未估计该模型（样本量不足、SOE 无变异或变量被效应吸收）。\n")
        return
    with open(p, "w", encoding="utf-8") as f:
        f.write(str(res.summary))


def _corr_and_p(df: pd.DataFrame, cols: list) -> tuple:
    sub = df[cols].dropna()
    n = len(sub)
    R = sub.corr(method="pearson")
    P = pd.DataFrame(np.nan, index=R.index, columns=R.columns)
    for i, ci in enumerate(cols):
        for j, cj in enumerate(cols):
            if i >= j:
                continue
            pair = sub[[ci, cj]].dropna()
            m = len(pair)
            if m < 5:
                continue
            r, p = stats.pearsonr(pair[ci], pair[cj])
            P.loc[ci, cj] = P.loc[cj, ci] = p
    np.fill_diagonal(P.values, np.nan)
    return R, P, n


def _annot_corr(R: pd.DataFrame, P: pd.DataFrame) -> list:
    ann = []
    for i, ri in enumerate(R.index):
        row = []
        for j, cj in enumerate(R.columns):
            r = R.loc[ri, cj]
            if i == j:
                row.append("1")
                continue
            p = P.loc[ri, cj]
            stars = ""
            if pd.notna(p):
                if p < 0.01:
                    stars = "**"
                elif p < 0.05:
                    stars = "*"
            row.append(f"{r:.2f}{stars}")
        ann.append(row)
    return ann


def _m4_slopes(res, years: list, ref_year: int):
    """由 M4 系数拼装各年 $\\\\partial Lev/\\\\partial NPR$ 及其近似 95% CI。"""
    cov = res.cov
    params = res.params
    std_err = res.std_errors
    rows = []
    pat = re.compile(r"\[T\.(\d{4})\]")
    for y in years:
        if y == ref_year:
            b = float(params["npr"])
            se = float(std_err["npr"])
        else:
            iname = None
            for name in params.index:
                if "npr:" in str(name) and f"[T.{y}]" in str(name):
                    iname = name
                    break
            if iname is None:
                continue
            b = float(params["npr"] + params[iname])
            c0, c1 = "npr", iname
            v = float(
                cov.loc[c0, c0]
                + cov.loc[c1, c1]
                + 2 * cov.loc[c0, c1]
            )
            se = float(np.sqrt(max(v, 0)))
        rows.append((y, b, b - 1.96 * se, b + 1.96 * se))
    return rows


def _marginal_npr_size(m5, sg: np.ndarray):
    r"""$\partial Lev/\partial NPR=\beta_0+\beta_1 Size+\beta_2 Size^2$ 及 Delta 方法 SE。"""
    names = ["npr", "npr_size", "npr_size2"]
    cov = m5.cov.loc[names, names]
    b = m5.params.loc[names].values.astype(float)
    me, ses = [], []
    for s in sg:
        g = np.array([1.0, s, s * s])
        me.append(float(g @ b))
        v = float(g @ cov.values @ g)
        ses.append(np.sqrt(max(v, 0.0)))
    me = np.array(me)
    se = np.array(ses)
    return me, me - 1.96 * se, me + 1.96 * se


def _regression_table_tex(models: dict, out: Path) -> None:
    """简易汇总表（LaTeX），列名为作业表 4.1 风格。"""
    spec = [
        ("NPR", "npr"),
        (r"NPR$\times$SOE", "npr_soe"),
        (r"$m2\_growth$", "m2_growth"),
        ("Size", "size"),
        ("Tang", "tang"),
        ("Growth", "growth"),
        ("NDTS", "ndts"),
    ]
    lines = [
        r"\begin{tabular}{l" + "c" * len(models) + "}",
        r"\hline",
        " & " + " & ".join(models.keys()) + r" \\",
        r"\hline",
    ]
    for lab, par in spec:
        cells = [lab]
        for res in models.values():
            if res is None or par not in res.params.index:
                cells.append("--")
                continue
            b = float(res.params[par])
            se = float(res.std_errors[par])
            cells.append(rf"{b:.4f} \ ({se:.4f})")
        lines.append(" & ".join(cells) + r" \\")
    lines.extend([r"\hline", r"\end{tabular}"])
    out.write_text("\n".join(lines), encoding="utf-8")


def _fig7_threshold(df: pd.DataFrame, fname: str, title: str) -> None:
    bal = df.groupby("stkcd").filter(lambda x: len(x) >= max(6, int(df["year"].nunique() // 3)))
    if len(bal) < 40:
        bal = df.copy()
    sg = np.quantile(bal["size"].values, np.linspace(0.12, 0.88, min(40, max(10, len(bal) // 20))))
    ssr = []
    for g in sg:
        d = bal.assign(
            npr_low=bal["npr"] * (bal["size"] <= g).astype(float),
            npr_high=bal["npr"] * (bal["size"] > g).astype(float),
        )
        try:
            r = _twfe(
                "lev ~ 1 + npr_low + npr_high + size + tang + growth + ndts + EntityEffects + TimeEffects",
                d,
            )
            if r is None:
                continue
            rv = np.asarray(r.resids).ravel()
            rss = float(np.dot(rv, rv))
            ssr.append((g, rss))
        except Exception:
            continue
    if not ssr:
        return
    S = pd.DataFrame(ssr, columns=["gamma", "rss"])
    rmin = S["rss"].min()
    S["lr"] = len(bal) * np.log(S["rss"] / rmin + 1e-12)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(S["gamma"], S["lr"], color="purple", linewidth=2)
    apply_cn(ax, title=title, xlabel=r"门槛 $\gamma$（$Size_{it}=\ln TA$）", ylabel=r"LR$^*$ 统计量（单门槛搜索）")
    plt.tight_layout()
    fig.savefig(FIG / fname, dpi=150)
    plt.close()


def run_all(df: pd.DataFrame) -> None:
    df = df.copy()
    df["year"] = df["year"].astype(int)

    vars_ = ["lev", "npr", "size", "tang", "growth", "ndts"]
    if "liq" in df.columns and df["liq"].notna().sum() > 10:
        vars_.append("liq")

    notes = ROOT / "output" / "model_notes.txt"
    notes.write_text(
        "模型说明（与 ex_P03 对齐要点）\n"
        "================================\n"
        "1. M1 双向固定效应（TWFE）：\n"
        r"   $$Lev_{it}=\alpha_i+\lambda_t+\beta\,NPR_{it}+\boldsymbol{\gamma}'\mathbf{X}_{it}+\varepsilon_{it}$$"
        "\n"
        "   标准误：Cameron–Gelbach–Miller 型 **公司与年度双向聚类**（linearmodels）。\n"
        "2. M1′：在 TWFE 中加入可观测宏观变量 $m2\\_growth_t$；"
        "完整交互固定效应（IFE）形式为\n"
        r"   $$Lev_{it}=\alpha_i+\beta NPR_{it}+\theta\, m2\\_growth_t+\boldsymbol{\lambda}_i'\boldsymbol{f}_t+\cdots$$"
        "\n"
        "   需 Stata regife 或等价程序估计；本仓库以 **M2 增速控制 + TWFE** 作可复现近似。\n"
        "3. M3 中 $SOE_i$ 主效应被 $\\alpha_i$ 吸收，仅交互项 $NPR\\times SOE$ 可识别斜率差异。\n",
        encoding="utf-8",
    )

    rows = []
    for lab, sub in [
        ("全样本", df),
        ("国有企业", df[df["soe"] == 1]),
        ("民营企业", df[df["soe"] == 0]),
    ]:
        for v in vars_:
            if v not in sub.columns:
                continue
            x = pd.to_numeric(sub[v], errors="coerce").dropna()
            if len(x) == 0:
                continue
            rows.append(
                {
                    "分组": lab,
                    "变量": v,
                    "N": len(x),
                    "Mean": x.mean(),
                    "SD": x.std(),
                    "P10": x.quantile(0.1),
                    "P25": x.quantile(0.25),
                    "Median": x.median(),
                    "P75": x.quantile(0.75),
                    "P90": x.quantile(0.9),
                }
            )
    pd.DataFrame(rows).to_csv(FIG.parent / "descriptive_by_group.csv", index=False, encoding="utf-8-sig")

    tt_rows = []
    for v in vars_:
        if v not in df.columns:
            continue
        a = df.loc[df["soe"] == 1, v].dropna()
        b = df.loc[df["soe"] == 0, v].dropna()
        if len(a) > 5 and len(b) > 5:
            t, p = stats.ttest_ind(a, b, equal_var=False)
            sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
            tt_rows.append({"变量": v, "t值": t, "p值": p, "显著性": sig})
    pd.DataFrame(tt_rows).to_csv(FIG.parent / "ttest_soe_nonsoe.csv", index=False, encoding="utf-8-sig")

    # ---------- Fig1：$\\overline{Lev}_t$（SOE 分组）----------
    g = df.groupby(["year", "soe"])["lev"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(9, 5))
    for s, lab in [(0, "非国有企业"), (1, "国有企业")]:
        sub = g[g["soe"] == s]
        ax.plot(sub["year"], sub["lev"], marker="o", label=lab, linewidth=2)
    apply_cn(
        ax,
        title=r"Fig.1 样本均值 $\overline{Lev}_t$（按 $SOE$ 分组）",
        xlabel="年度 $t$",
        ylabel=r"杠杆率：$Lev_{it}=TL_{it}/TA_{it}$（组内均值）",
    )
    legend_cn(ax, loc="best")
    plt.tight_layout()
    fig.savefig(FIG / "Fig1_lev_trend_soe.png", dpi=150)
    plt.close()

    # ---------- 作业 §2.3 图2：$\\overline{NPR}_t$ ----------
    g2 = df.groupby(["year", "soe"])["npr"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(9, 5))
    for s, lab in [(0, "非国有企业"), (1, "国有企业")]:
        sub = g2[g2["soe"] == s]
        ax.plot(sub["year"], sub["npr"], marker="o", label=lab, linewidth=2)
    apply_cn(
        ax,
        title=r"图2（描述统计）样本均值 $\overline{NPR}_t$（按 $SOE$ 分组）",
        xlabel="年度 $t$",
        ylabel=r"净利润率 $NPR_{it}=\pi_{it}/TA_{it}$（组内均值）",
    )
    legend_cn(ax, loc="best")
    plt.tight_layout()
    fig.savefig(FIG / "Fig1b_npr_trend_soe.png", dpi=150)
    plt.close()

    # ---------- Fig2：Winsorize 前后（作业 §1.5 + §4.2 Fig2）----------
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, col, zh in zip(axes, ["lev", "npr", "growth"], [r"$Lev$", r"$NPR$", r"$Growth$"]):
        raw = pd.to_numeric(df[col + "_raw"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        w = pd.to_numeric(df[col], errors="coerce").dropna()
        ax.boxplot([raw, w], labels=["缩尾前", "缩尾后"])
        apply_cn(ax, title=rf"Fig.2 {zh}：截面 1% 双侧 Winsorize", ylabel=zh)
        if fp():
            ax.set_xticklabels(["缩尾前", "缩尾后"], fontproperties=fp())
    plt.tight_layout()
    fig.savefig(FIG / "Fig2_winsor_compare.png", dpi=150)
    plt.close()

    if "liq_raw" in df.columns and df["liq_raw"].notna().sum() > 20:
        fig, ax = plt.subplots(figsize=(5, 4))
        raw = pd.to_numeric(df["liq_raw"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        w = pd.to_numeric(df["liq"], errors="coerce").dropna()
        ax.boxplot([raw, w], labels=["缩尾前", "缩尾后"])
        apply_cn(ax, title=r"Fig.2c 选做：$Liq$（流动比）截面 1% Winsorize", ylabel=r"$Liq_{it}$")
        if fp():
            ax.set_xticklabels(["缩尾前", "缩尾后"], fontproperties=fp())
        plt.tight_layout()
        fig.savefig(FIG / "Fig2c_liq_winsor_optional.png", dpi=150)
        plt.close()

    fig, ax = plt.subplots(figsize=(12, 5))
    years = sorted(df["year"].unique())
    data_box = [df.loc[df["year"] == y, "lev"].dropna().values for y in years]
    ax.boxplot(data_box, labels=[str(y) for y in years], showfliers=False)
    apply_cn(
        ax,
        title=r"图3（描述统计）$Lev_{it}$ 分年度箱线图",
        xlabel="年度 $t$",
        ylabel=r"$Lev_{it}$",
    )
    plt.xticks(rotation=45)
    plt.tight_layout()
    fig.savefig(FIG / "Fig2b_lev_box_by_year.png", dpi=150)
    plt.close()

    # ---------- Fig3：Pearson + 5% 显著性 ----------
    ccols = [c for c in ["lev", "npr", "size", "tang", "growth", "ndts", "soe"] if c in df.columns]
    R, P, n_obs = _corr_and_p(df, ccols)
    ann = _annot_corr(R, P)
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    sns.heatmap(
        R,
        annot=ann,
        fmt="",
        cmap="RdBu_r",
        center=0,
        ax=ax,
        vmin=-1,
        vmax=1,
        annot_kws=heatmap_annot_kw(),
    )
    t = f"Fig.3 主要变量 Pearson 相关（$N={n_obs}$；* $p$<0.05，** $p$<0.01）"
    if fp():
        ax.set_title(t, fontproperties=fp())
    else:
        ax.set_title(t)
    plt.tight_layout()
    fig.savefig(FIG / "Fig3_corr_heatmap.png", dpi=150)
    plt.close()
    P.to_csv(FIG.parent / "corr_pvalues.csv", encoding="utf-8-sig")

    f_base = "lev ~ 1 + npr + size + tang + growth + ndts + EntityEffects + TimeEffects"
    m1 = _twfe(f_base, df)
    _save_summary("M1_TWFE", m1)

    m2a = _twfe(f_base, df.query("soe==1"))
    m2b = _twfe(f_base, df.query("soe==0"))
    _save_summary("M2_SOE", m2a)
    _save_summary("M2_NonSOE", m2b)

    m3 = None
    wald_path = FIG.parent / "wald_M3_npr_soe.txt"
    if df["soe"].nunique() >= 2:
        df = df.copy()
        df["npr_soe"] = df["npr"] * df["soe"]
        f3 = "lev ~ 1 + npr + npr_soe + size + tang + growth + ndts + EntityEffects + TimeEffects"
        m3 = _twfe(f3, df)
        if m3 is not None:
            try:
                wald_path.write_text(str(m3.wald_test("npr_soe = 0")), encoding="utf-8")
            except Exception:
                wald_path.write_text(
                    "Wald 检验未执行（样本或秩条件）。\n", encoding="utf-8"
                )
        else:
            wald_path.write_text(
                "M3 未估计成功，无 Wald 检验（秩不足或变量被吸收）。\n", encoding="utf-8"
            )
    else:
        wald_path.write_text(
            "未估计 M3：全样本 $SOE$ 无跨公司变异，无法识别 $NPR\\times SOE$。\n",
            encoding="utf-8",
        )
    _save_summary("M3_interaction", m3)

    f1p = "lev ~ 1 + npr + size + tang + growth + ndts + m2_growth + EntityEffects + TimeEffects"
    m1p = _twfe(f1p, df.dropna(subset=["m2_growth"]))
    _save_summary("M1_prime_IFE_proxy", m1p)

    years_u = sorted(df["year"].unique())
    ref_y = 2010 if 2010 in years_u else years_u[0]
    f4 = (
        f"lev ~ 1 + npr + npr:C(C(year, Treatment(reference={ref_y}))) + "
        "size + tang + growth + ndts + EntityEffects + TimeEffects"
    )
    m4 = _twfe(f4, df)
    _save_summary("M4_time_varying_NPR", m4)

    # ---------- Fig4：M3 调节（斜率组合）----------
    if m3 is None or df["soe"].nunique() < 2:
        b_npr, b_ix = 0.0, 0.0
        fig_title = r"Fig.4 $SOE$ 调节：样本内 $SOE$ 无变异，仅展示 $\partial Lev/\partial NPR$（民企）"
    else:
        b = m3.params
        b_npr = float(b.get("npr", 0.0))
        b_ix = float(b.get("npr_soe", 0.0))
        fig_title = r"Fig.4 $SOE$ 调节：$\partial Lev/\partial NPR$（民企 $\hat\beta_1$；国企 $\hat\beta_1+\hat\beta_2$）"
    npr_grid = np.linspace(df["npr"].quantile(0.05), df["npr"].quantile(0.95), 60)
    fig, ax = plt.subplots(figsize=(7, 5))
    y0 = b_npr * (npr_grid - npr_grid.mean())
    y1 = (b_npr + b_ix) * (npr_grid - npr_grid.mean())
    ax.plot(npr_grid, y0, label=r"非国企：斜率 $\hat\beta_1$", linewidth=2)
    if df["soe"].nunique() >= 2 and m3 is not None:
        ax.plot(npr_grid, y1, label=r"国企：斜率 $\hat\beta_1+\hat\beta_2^{NPR\times SOE}$", linewidth=2)
    apply_cn(ax, title=fig_title, xlabel=r"$NPR_{it}$", ylabel=r"相对变化（控制变量取均值，线性近似）")
    legend_cn(ax)
    plt.tight_layout()
    fig.savefig(FIG / "Fig4_moderation_npr_soe.png", dpi=150)
    plt.close()

    # ---------- Fig5：M4 $\\hat\\beta_t$ ----------
    if m4 is not None:
        betas = _m4_slopes(m4, years_u, ref_y)
    else:
        betas = []
    if not betas:
        n_f = int(df["stkcd"].nunique())
        min_firms_year = max(5, min(30, max(int(0.6 * n_f), n_f - 4)))
        for y in years_u:
            sub = df[df["year"] == y]
            if sub["stkcd"].nunique() < min_firms_year:
                continue
            try:
                r = _twfe(
                    "lev ~ 1 + npr + size + tang + growth + ndts + EntityEffects",
                    sub,
                    min_rows=max(12, min_firms_year),
                    min_entities=min_firms_year,
                )
                if r is None:
                    continue
                ci = r.conf_int().loc["npr"]
                betas.append(
                    (y, float(r.params["npr"]), float(ci["lower"]), float(ci["upper"]))
                )
            except Exception:
                continue
    if betas:
        B = pd.DataFrame(betas, columns=["year", "beta", "lo", "hi"])
        B.to_csv(FIG.parent / "m4_beta_npr_by_year.csv", index=False, encoding="utf-8-sig")
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(B["year"], B["beta"], "o-", color="steelblue", label=r"$\hat\beta_t^{NPR}$")
        ax.fill_between(B["year"], B["lo"], B["hi"], color="steelblue", alpha=0.25, label="95% CI")
        kw_txt = {"ha": "center", "fontsize": 8, "color": "gray"}
        if fp():
            kw_txt["fontproperties"] = fp()
        for yr, lab in [(2015, "2015"), (2018, "2018"), (2020, "2020"), (2022, "2022")]:
            if yr in set(B["year"]):
                ax.axvline(yr, color="gray", linestyle=":", alpha=0.7)
                ax.text(yr, ax.get_ylim()[1], lab, **kw_txt)
        apply_cn(
            ax,
            title=r"Fig.5 时变系数：$\hat\beta_t$（$NPR_{it}\!\to\!Lev_{it}$；主规格为 M4 TWFE+年交互）",
            xlabel="年度 $t$",
            ylabel=r"$\hat\beta_t$",
        )
        legend_cn(ax, loc="best")
        plt.tight_layout()
        fig.savefig(FIG / "Fig5_time_varying_beta.png", dpi=150)
        plt.close()

    df = df.copy()
    df["npr_size"] = df["npr"] * df["size"]
    df["npr_size2"] = df["npr"] * (df["size"] ** 2)
    f5 = "lev ~ 1 + npr + npr_size + npr_size2 + size + tang + growth + ndts + EntityEffects + TimeEffects"
    m5 = _twfe(f5, df)
    _save_summary("M5_functional_coefficient", m5)
    if m5 is not None and all(x in m5.params.index for x in ["npr", "npr_size", "npr_size2"]):
        sg = np.linspace(df["size"].quantile(0.05), df["size"].quantile(0.95), 100)
        me, lo, hi = _marginal_npr_size(m5, sg)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(sg, me, color="darkgreen", linewidth=2, label=r"$\hat\beta(Size)=\partial Lev/\partial NPR$")
        ax.fill_between(sg, lo, hi, color="darkgreen", alpha=0.2, label="95% 置信带")
        kw_txt = {"ha": "center", "fontsize": 8}
        if fp():
            kw_txt["fontproperties"] = fp()
        for q, lab in zip([0.1, 0.25, 0.5, 0.75, 0.9], ["P10", "P25", "Median", "P75", "P90"]):
            xq = float(df["size"].quantile(q))
            ax.axvline(xq, color="gray", linestyle=":", alpha=0.6)
            ax.text(xq, ax.get_ylim()[1] * 0.95, lab, **kw_txt)
        apply_cn(
            ax,
            title=r"Fig.6 函数系数：$\hat\beta(Size)$（多项式近似，M5）",
            xlabel=r"$Size_{it}=\ln(TA_{it})$",
            ylabel=r"$\partial Lev_{it}/\partial NPR_{it}$",
        )
        legend_cn(ax, loc="best")
        plt.tight_layout()
        fig.savefig(FIG / "Fig6_beta_size_poly.png", dpi=150)
        plt.close()

    _fig7_threshold(
        df,
        "Fig7_threshold_lr.png",
        r"Fig.7 单门槛 LR 统计量（$Size$ 为门槛变量，Hansen 思路的网格搜索）",
    )
    sub1525 = df[(df["year"] >= 2015) & (df["year"] <= 2025)].copy()
    _fig7_threshold(
        sub1525,
        "Fig7b_threshold_lr_2015_2025.png",
        r"Fig.7b 子样本 $t\in[2015,2025]$：门槛 LR（稳健性）",
    )

    _regression_table_tex(
        {
            "M1:TWFE": m1,
            "M1$'$:IFE-proxy": m1p,
            "M2a:SOE": m2a,
            "M2b:NonSOE": m2b,
            "M3": m3,
        },
        TAB / "reg_m1_m3_summary.tex",
    )

    print("[analysis] 图表 ->", FIG)
    print("[analysis] 表格 ->", TAB)
