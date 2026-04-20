# 上市公司资本结构影响因素分析（P03）

> [作业要求 ex_P03](https://github.com/lianxhcn/dsfin/blob/main/homework/ex_P03_Panel-capital_strucuture.md)

## 个人信息

- 姓名：姬亚楠
- 邮箱：（请填写）

## 核心理论与计量设定（LaTeX）

**权衡理论**预测 $NPR_{it}$ 与杠杆率 $Lev_{it}$ 正相关；**优序融资理论**预测二者负相关。基准 **双向固定效应（TWFE）** 模型为

$$
Lev_{it} = \alpha_i + \lambda_t + \beta\, NPR_{it} + \boldsymbol{\gamma}'\mathbf{X}_{it} + \varepsilon_{it},
\quad
\mathbf{X}_{it} = (Size_{it}, Tang_{it}, Growth_{it}, NDTS_{it})'.
$$

**M1′（交互固定效应 IFE）** 在讲义中的形式为

$$
Lev_{it} = \alpha_i + \beta\, NPR_{it} + \theta\, m2\_growth_t + \boldsymbol{\lambda}_i' \boldsymbol{f}_t + \boldsymbol{\gamma}'\mathbf{X}_{it} + \varepsilon_{it}.
$$

本仓库用 **TWFE + 可观测 $m2\_growth_t$** 作可复现的 **IFE 近似**；若需与 Stata `regife` 完全对齐，请在 Stata 中估计并替换结果。

**M3 调节效应**（含 $SOE_i$ 虚拟变量）为

$$
Lev_{it} = \alpha_i + \lambda_t + \beta_1 NPR_{it} + \beta_2 (NPR_{it} \times SOE_i) + \boldsymbol{\gamma}'\mathbf{X}_{it} + \varepsilon_{it}.
$$

由于 $\alpha_i$ 吸收时不变的 $SOE_i$ 主效应，报告时强调 **斜率差异** $\hat\beta_2$ 的经济含义。

**M5 函数系数（多项式）**：$\beta(Size_{it}) = \beta_0 + \beta_1 Size_{it} + \beta_2 Size_{it}^2$，边际效应 $\partial Lev/\partial NPR = \beta(Size_{it})\cdot$ 对 $NPR$ 的线性部分见 `codes/analysis_run.py`。

**M6 门槛**：以 $Size$ 为门槛变量，在 TWFE 残差平方和网格上构造 LR 型曲线（Fig.7 / Fig.7b），与 Hansen(1999) 正式检验流程对齐思路；全样本 **平衡面板** 门槛请仍以 Stata `xthreg` 为金标准。

## 数据来源

| 内容 | 本仓库默认来源 |
|------|----------------|
| 三大表（年报） | AkShare → 东方财富 `stock_*_by_yearly_em` |
| 行业 / 国企识别 | 巨潮 `stock_industry_change_cninfo`、`stock_profile_cninfo` |
| ST 名单 | `stock_zh_a_st_em`（**截面**；作业「曾 ST」需 CSMAR） |
| M2 | `macro_china_money_supply` |

若必须使用 **CSMAR**：将官方 CSV 放入 `data/raw/`，文件名与作业一致（`balance_sheet.csv` 等），列名与 `codes/panel_build.py` 中字段一致即可。

下载时间：最近一次运行 `python run_p03.py --download` 时写入 `data/raw/.download_complete`。

## 环境

```bash
cd dshw-p03
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

- Python 3.9+
- 主回归：`linearmodels.PanelOLS`；标准误 **公司与年度双向聚类**（对齐 `vce(cluster stkcd year)` 思路）。

## 运行

```bash
# 首次或更新原始数据（需网络）：
P03_MAX_STOCKS=100 .venv/bin/python run_p03.py --download

# 已有 data/raw/ 时：
.venv/bin/python run_p03.py
```

- `P03_MAX_STOCKS`：拉取股票数上限（默认 100）；**若样本内 $SOE$ 无变异，请增大该值以包含国企**。
- 若你过去使用旧目录 `data_raw/`，程序会在首次运行时 **自动复制** 到 `data/raw/`。

## 输出（与作业目录对齐）

| 路径 | 说明 |
|------|------|
| `data/raw/` | 原始 CSV（作业要求；GitHub 勿提交） |
| `data/clean/panel_final.csv` | 清洗后面板 |
| `data/clean/sample_flow.csv` | §1.3 筛选流程表 |
| `output/figures/Fig*.png` | Fig.1–Fig.7 及 Fig.7b、描述性图 |
| `output/tables/reg_m1_m3_summary.tex` | M1–M3 等系数汇总（LaTeX） |
| `output/reg_*.txt` | 各模型详细回归输出 |
| `output/model_notes.txt` | 模型设定与 Stata/IFE 差异说明 |

## 选做加分：Quarto Book → GitHub Pages

**一步步教你做的说明**（本机预览、建仓库、开 Pages、填 README 链接）：请打开仓库根目录的 **[`QUARTO_PUBLISH.md`](./QUARTO_PUBLISH.md)**。

已预置：`_quarto.yml`、`index.qmd`、`chapters/*.qmd`，以及 **GitHub Actions**（推送 `main`/`master` 后自动 `quarto render` 并部署到 Pages）。你主要需在 GitHub **Settings → Pages** 把来源选为 **GitHub Actions**。

## GitHub 仓库

- https://github.com/sunzhen123-lab/dshw--panel

## Quarto Book（GitHub Pages 发布后使用此链接）

- https://sunzhen123-lab.github.io/dshw--panel/

## 与 ex_P03 逐项对照（实现状态）

| 作业要求 | 本仓库实现 |
|----------|------------|
| §1.1 路径 `data/raw/` | 已采用；旧 `data_raw/` 首次运行自动迁移 |
| §1.2 变量 $Lev,NPR,Size,Tang,Growth,NDTS,SOE$ | `panel_build.py` 按定义构造；$Growth$ 按公司 `shift(1)` |
| §1.2 选做 $Liq$ | 有；截面 Winsorize 并出 **Fig2c** |
| §1.3 筛选顺序与流程表 | `data/clean/sample_flow.csv` 与作业顺序一致 |
| §1.4 行业小类合并 | 制造业 2 位、小样本 $<30$ 并至 CM_other |
| §1.5 Winsorize（按年 1%） | $Lev,NPR,Tang,Growth,NDTS$（及 $Liq$）；Fig.2 对比图 |
| §2.1–2.2 描述统计 / 相关 / t 检验 | `descriptive_by_group.csv`、`corr_pvalues.csv`、Fig.3 带 $p$ 值星标 |
| §2.3 时序与箱线图 | Fig.1、Fig.1b（NPR）、Fig.2b（Lev 分年箱线） |
| M1 TWFE + **双向聚类** | `linearmodels` `clusters=(stkcd,year)` |
| M1′ IFE | **TWFE + `m2_growth`**；纯时间序列宏观变量可能被年度 FE 吸收，与 M1 系数重合时属预期现象 |
| M2 分组 + Chow | 分组回归；全样本 Wald 见 `wald_M3_npr_soe.txt`（需 M3 可估时） |
| M3 交互项 + Fig.4 | 需 $SOE$ 有 0/1 变异；否则 Fig.4 为单组示意 |
| M4 + Fig.5 | 年$\times NPR$ 交互 TWFE；失败时回退分年截面回归 |
| M5 + Fig.6 置信带 | 多项式交互 + Delta 方法 95% 带 |
| M6 + Fig.7 / 子样本 Fig.7b | LR 网格；**2015–2025** 稳健性 |
| 加分 Quarto Book | 已含 `_quarto.yml` 与 `chapters/`；本地 `quarto render` 生成 `_book/` |

## 主要发现（运行后据 `output/reg_M1_TWFE.txt` 填写）

1. TWFE 下 $\hat\beta^{NPR}$ 的符号与显著性：……
2. 国企 vs 民企（M2）：……
3. 调节 / 时变 / 规模异质性（M3–M6）：……
