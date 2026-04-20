# Quarto Book 加分项：你需要做的事（按顺序）

仓库里已放好 **`_quarto.yml`**、`index.qmd`、`chapters/*.qmd`，以及 **`.github/workflows/publish-quarto.yml`**（推送后自动构建并发布）。下面是你**本人必须在 GitHub / 本机完成的步骤**。

---

## 一、本机预览（可选但推荐）

1. 安装 [Quarto](https://quarto.org/docs/get-started/)（官网下载安装包即可）。
2. 在终端进入本项目根目录（与 `_quarto.yml` 同级）：
   ```bash
   cd /path/to/dshw-p03
   quarto render
   ```
3. 成功后打开 **`_book/index.html`** 用浏览器查看排版与公式是否正常。

若 `quarto render` 报错，把完整终端输出复制给助教或 AI 排查即可。

---

## 二、GitHub 仓库（作业建议名：`dshw--panel`）

1. 在 GitHub 上 **New repository**，名称填 **`dshw--panel`**，选 **Public**。
2. **不要**在网页上勾选自动添加 README（避免与本地冲突）；建好后按页面提示推送本地代码：
   ```bash
   cd /path/to/dshw-p03
   git init
   git add .
   git commit -m "P03 panel + Quarto book scaffold"
   git branch -M main
   git remote add origin https://github.com/sunzhen123-lab/dshw--panel.git
   git push -u origin main
   ```
3. 作业要求：**仓库里不要提交 `data/raw/`**（本仓库 `.gitignore` 已忽略）；坚果云 zip 里再单独带上原始数据即可。

---

## 三、打开 GitHub Pages（关键一步）

1. 打开仓库 **Settings → Pages**。
2. **Build and deployment** 里，**Source** 选 **GitHub Actions**（不要选 Deploy from a branch）。
3. 保存后，再随便改一个字提交推送，或到 **Actions** 里手动运行 **Publish Quarto Book** 工作流。
4. 等 workflow 绿勾完成后，同一 **Settings → Pages** 页面会显示站点地址，一般是：  
   **`https://sunzhen123-lab.github.io/dshw--panel/`**  
   （若仓库名不是 `dshw--panel`，把路径里的仓库名改成你的仓库名。）

> 第一次用 Pages 时，若 Actions 里没有 “Pages” 权限，GitHub 有时会提示在仓库 Settings 里批准 **Workflow permissions**（读/写 Contents 一般不用；Pages 写入由 workflow 里的 `permissions` 声明）。

---

## 四、写进作业要求的 README

把下面两处改成你的真实链接（提交前在 `README.md` 里改）：

- **GitHub 仓库**：`https://github.com/sunzhen123-lab/dshw--panel`
- **Quarto Book（GitHub Pages）**：`https://sunzhen123-lab.github.io/dshw--panel/`（Actions 部署成功后生效）

---

## 五、你**不用**手动做的事（已替你配好）

| 项目 | 说明 |
|------|------|
| 书稿骨架 | `_quarto.yml` + `index.qmd` + `chapters/*.qmd` |
| 自动发布 | `.github/workflows/publish-quarto.yml` 在 push 到 `main`/`master` 时 `quarto render` 并部署 `_book/` |
| 输出目录 | `_book/`（已在 `.gitignore` 中忽略，避免把渲染结果当源码提交） |

---

## 六、常见问题

- **Actions 失败：找不到 quarto**  
  工作流已使用 `quarto-dev/quarto-actions/setup@v2`，一般无需本机安装；若仍失败，看 Actions 日志里是否网络问题，可重试。

- **站点 404**  
  确认 Pages 的 Source 是 **GitHub Actions**；仓库须为 **Public**（或付费私有 + Pages 规则允许）。

- **想改章节结构**  
  编辑 `_quarto.yml` 里 `book.chapters` 列表顺序，或增删 `chapters/xx_xxx.qmd` 文件即可。

---

更完整的官方说明见课程链接：[Quarto Book 教程](https://lianxhcn.github.io/quarto_book/) 与 [dsfin `_quarto.yml`](https://github.com/lianxhcn/dsfin/blob/main/_quarto.yml)。
