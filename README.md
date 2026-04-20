# 上市公司资本结构影响因素分析

> **作业要求**：[ex_P03 — 上市公司资本结构：面板数据模型实证](https://github.com/lianxhcn/dsfin/blob/main/homework/ex_P03_Panel-capital_strucuture.md)  
> **GitHub 仓库（个人）**：https://github.com/sunzhen123-lab/dshw--panel  
> **Quarto Book（GitHub Pages）**：https://sunzhen123-lab.github.io/dshw--panel/

---

## 个人信息

- **姓名**：姬亚楠  
- **邮箱**：nannan714521.163.com
- **说明**：本题为**个人作业**；仓库与 Pages 均为本人账号维护，无小组仓库。

---

## 数据来源

- **实际使用**：AkShare / 东方财富（年报三大表）、巨潮行业与公司概况、东方财富 ST 名单截面、人民银行 M2 序列；**非 CSMAR 导出**。若课程强制 CSMAR，可将官方 CSV 放入 `data/raw/` 并保持与 `codes/panel_build.py` 一致的列名。  
- **下载时间**：以 `data/raw/.download_complete` 文件生成时间为准（最近一次执行 `python run_p03.py --download`）。  
- **最终样本（当前打包内结果）**：**14** 家公司，**199** 个观测值，**2010–2025** 年（以 `data/clean/panel_final.csv` 为准；扩大 `P03_MAX_STOCKS` 可更新全样本）。

---

## 样本筛选流程（对应 ex_P03 §1.3）

| 筛选步骤 | 剔除观测数 | 剩余观测数 | 剩余公司数 |
|---------|-----------|-----------|-----------|
| 初始样本（2010–2025，合并年报后） | — | 231 | 15 |
| 剔除金融、保险行业（证监会 J / 门类名含金融、保险） | 16 | 215 | 14 |
| 剔除 ST/PT 相关公司（当前风险警示名单近似；曾 ST 全历史需 CSMAR） | 0 | 215 | 14 |
| 剔除资不抵债（$Lev>1$） | 4 | 211 | 14 |
| 剔除关键变量缺失 | 12 | 199 | 14 |
| **最终样本** | — | **199** | **14** |

（与 `data/clean/sample_flow.csv` 一致。）

---

## 工具

- **Python**：3.9+（数据处理与计量；主回归为 `linearmodels.PanelOLS`，公司与年度**双向聚类**标准误）。  
- **Jupyter Notebook**：`01_data_clean.ipynb`、`02_EDA_analysis.ipynb`、`03_empirical_models.ipynb`。  
- **Stata**：未作为主线使用（无 `.do` 文件）；与讲义 Stata 命令对照见 `output/model_notes.txt`。

---

## 目录与运行

解压后进入项目根目录（与 `run_p03.py` 同级），执行：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# 已有 data/raw/ 时：
.venv/bin/python run_p03.py
# 需重新拉取原始数据时（需网络）：
P03_MAX_STOCKS=100 .venv/bin/python run_p03.py --download
```

- 原始数据路径：**`data/raw/`**（坚果云压缩包内已包含，满足「解压后可运行」）。  
- 清洗结果：**`data/clean/panel_final.csv`**；图与回归输出：**`output/`**。

---

## 主要发现（3–5 条，基于当前 `output/reg_M1_TWFE.txt`）

1. **M1（TWFE）**：$NPR$ 系数 $\hat\beta\approx 0.028$，在 5% 水平显著为正（$p\approx 0.023$），与**权衡理论**预测方向一致；全样本解释力以 Within $R^2$ 为主，见回归摘要。  
2. **样本与产权**：当前下载股票数较少，**国企子样本不足**，M2 国企/M3 交互部分为占位说明；扩大 `P03_MAX_STOCKS` 并重新下载可完善 SOE 分析。  
3. **时变与异质性**：Fig.5（M4）、Fig.6–7（M5/M6）已生成；门槛子样本见 Fig.7b（2015–2025）。  
4. **M1′**：以 TWFE + `m2_growth` 作 IFE 的可复现代理；纯宏观年度变量可能被年度 FE 吸收，与讲义 `regife` 完整设定差异见 `output/model_notes.txt`。

---

## 提交与加分说明

- **坚果云压缩包**（[ex_P03 提交要求](https://github.com/lianxhcn/dsfin/blob/main/homework/ex_P03_Panel-capital_strucuture.md)）：课程示例为 **`exP03_姓名.zip`**。已生成本人 **`exP03_姬亚楠.zip`** 与 **`exP03_姬亚楠.tar.gz`**（**tar 包**），位于 **`dshw-p03` 的上一级目录**（例如本机路径 **`…/jiyanan/exP03_姬亚楠.tar.gz`**，与文件夹 `dshw-p03` 并列）。内含顶层文件夹 **`exP03_姬亚楠/`**，其中有 **`data/raw/`**、`output/`、全部 **`.ipynb`**、**`README.md`**、**`codes/`** 等，解压后进入该文件夹即可按上文命令运行。  
- **重新打包**：在仓库内执行 `bash scripts/pack_submission.sh` 会在上一级目录覆盖生成上述两个文件。  
- **GitHub**：仓库 [sunzhen123-lab/dshw--panel](https://github.com/sunzhen123-lab/dshw--panel) 按课程要求不提交 `data/raw/`；**原始数据以坚果云压缩包为准**。  
- **Quarto Book**：见 [`QUARTO_PUBLISH.md`](./QUARTO_PUBLISH.md)；线上站点：<https://sunzhen123-lab.github.io/dshw--panel/>（需 Pages 已启用 Actions 部署）。

---

## 附录：核心模型（LaTeX，与讲义一致）

**TWFE（M1）**

$$
Lev_{it} = \alpha_i + \lambda_t + \beta\, NPR_{it} + \boldsymbol{\gamma}'\mathbf{X}_{it} + \varepsilon_{it},
\quad
\mathbf{X}_{it} = (Size_{it}, Tang_{it}, Growth_{it}, NDTS_{it})'.
$$

**M3（调节，$SOE_i$ 主效应被 $\alpha_i$ 吸收）**

$$
Lev_{it} = \alpha_i + \lambda_t + \beta_1 NPR_{it} + \beta_2 (NPR_{it} \times SOE_i) + \boldsymbol{\gamma}'\mathbf{X}_{it} + \varepsilon_{it}.
$$

更多实现细节与 ex_P03 逐项对照，见历史版本或仓库内 `codes/` 注释。
