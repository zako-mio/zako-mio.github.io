# GitHub 新手全功能 DAG 教程

面向**完全没用过 GitHub** 的读者的交互式功能关系图谱教程。GitHub 的几十个功能不是孤立的——仓库、分支、提交、Release、Fork、PR、Issue、Actions……彼此依赖、互相承接。本教程用一张**功能关系图谱（DAG）**把它们的依赖关系讲清楚。

## 快速开始

| 想做什么 | 去哪 |
|---------|------|
| 🎯 交互式功能关系图（推荐第一个打开） | `04-interactive/index.html` |
| 🗂️ 功能组目录 | `03-groups/index.html` |
| 📄 每个功能一页（介绍/双轨操作/关系/小结） | `02-pages/`（35 页） |
| 🖼️ 关键流程图（静态） | `05-drawio/`（6 张 drawio+png） |
| 🤖 AI 友好 MD 镜像 | `06-md/`（索引/分组/分层/全节点） |
| 📚 教程对比分析报告 | `09-tutorial-analysis/analysis.html`（HTML 人类阅读版；同目录 analysis.md 为 AI 源文件） |
| 📊 DAG 数据 | `01-dag-data/github-dag.json` |

## 目录结构

```
0817-github-dag/
├── 01-dag-data/          # DAG 数据: github-dag.json (35节点 + 41边 + 7组 + 9层)
├── 02-pages/             # 每功能一页 HTML（35 页）
├── 03-groups/            # 7 组索引页 + 组目录
├── 04-interactive/       # cytoscape 交互总览（组级视图+点击下钻）+ vendor
├── 05-drawio/            # 6 张关键流程图（全貌/Git vs GitHub/仓库生命周期/Fork→PR/Release/Actions）
├── 06-md/                # AI 友好 MD 镜像
├── 07-checkpoint/        # 中间产物与生成脚本（合并/生成/门控）
└── 09-tutorial-analysis/ # 教程对比分析报告（analysis.html 人类阅读版 + analysis.md AI 源文件）
```

## 核心数据

- **35 功能节点**：G00 前置概念(2) / G01 账号与仓库(6) / G02 版本管理(7) / G03 协作(5) / G04 项目管理(5) / G05 自动化部署(4) / G06 工具生态(6)
- **41 关系边**，四种语义：
  - 🔶 **前置依赖（PREREQ）**：先学会它才能做这件事
  - 🟢 **包含从属（CONTAINS）**：它建立在另一个功能之上
  - 🟣 **概念升级（UPGRADE）**：理解后帮助你进阶到更高层次
  - 🔵 **流程承接（FLOW）**：前一步的产出被后一步消费
- **9 拓扑层**：层序 = 学习顺序（Layer 0 版本控制基础 → Layer 8 包管理）
- **边方向 = 学习顺序**：A→B 表示先学 A 再学 B

## 内容来源与交叉验证

- **官方**：docs.github.com 全流程文档（Get started / Repositories / Pull requests / Actions / Issues / Pages / Packages / Code security / CLI / Desktop / API / Codespaces / Gists）
- **英文权威教程**：GitHub Hello World、freeCodeCamp、Atlassian Git Tutorials、Pro Git 书、GeeksforGeeks、GitHub Skills
- **中文高赞教程**：菜鸟教程、廖雪峰 Git 教程、阮一峰博客、CSDN 新手文
- 4 路联网调研（代理 127.0.0.1:7890 + Google）→ 交叉验证 → 教程分析报告驱动编写
- **历史维度**（二次迭代）：3 路调研（git-scm 书 / github.blog 官方公告 / 维基百科）为每功能页补充"历史背景"区块（诞生时间/当时痛点/需求变迁/历史教训，全可溯源）。年份以官方一手来源为准（如 Issues=2009、正式 Reviews=2016、Fork 2008 已可用）

## 拓扑分层速览

- **Layer 0**（1）：版本控制基础
- **Layer 1**（3）：Git vs GitHub / Git 命令行基础 / Gist
- **Layer 2**（3）：账号与Profile / Commit / GitHub CLI
- **Layer 3**（3）：创建仓库 / Branch / Tag
- **Layer 4**（13）：仓库骨架 / 远程仓库 / Star Watch / 协作者权限 / Issue / 讨论区 / 维基 / Dependabot / API / Codespaces / Merge / Pages / Release
- **Layer 5**（6）：克隆仓库 / Push Pull / Fork / Notifications / Team / Milestone
- **Layer 6**（2）：Desktop / Pull Request
- **Layer 7**（3）：Code Review / Projects看板 / Actions
- **Layer 8**（1）：Packages

## 质量门控

- JSON 合法 / DAG 无环 / 35 节点全字段 / HTML 断链检查 / drawio-png 配套 / MD 覆盖 / headless+VLM 视觉验证（详见 `07-checkpoint/quality-gate.py`）
