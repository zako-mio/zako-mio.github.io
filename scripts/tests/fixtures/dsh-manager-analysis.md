# dsh-manager 插件深度分析

对 [`as1350/dsh-manager`](https://github.com/as1350/dsh-manager)（@deepseek-ai/dsh-manager v0.35.6, commit `ebbe995`）的插件级深度分析：依赖关系 / 功能实现 / 需求溯源 / 设计问题与建议。

方法论对齐 [deepseek-harness-plugin-dag](https://github.com/zako-mio/deepseek-harness-plugin-dag) 知识库的三硬依据框架：

- **E1 编译依赖** — package.json peerDependencies / dependencies / import
- **E2 运行时依赖** — ctx 服务注入 / ctx.get / 事件订阅
- **E3 组合依赖** — cordis.patch.yml 装配位置

所有结论附 `lib/xxx.js:行号` 源码引用，逐条可溯源。

## 快速开始

| 想做什么 | 去哪 |
|---------|------|
| **交互式依赖 DAG**（5 内部模块 + 18 宿主 stub + 23 边，点击节点看详情） | 直接浏览器打开 `dsh-manager-plugin-page.html` |
| 结构化分析数据（JSON，含全部证据） | `02-analysis/dag-data.json` |
| 分析报告（五段完整版） | `report.md` / `report.html` |
| 被分析的源码快照 | `01-source/dsh-manager/` |

## 核心结论速览

- **定位**：dsh Web 管理面板插件——Skills 管理 + 部署补丁管理器 + 本地仓库面板 + 本地服务面板
- **双半边架构**：node 半边 `inject:['webServer']` 经 `webServer.register` 挂 POST `/api/dsh-manager` 单路由（61 方法 RPC 面）；browser 半边经 `__DSH_BOOT__` 机制注入，`inject:['slots']` 注册 4 触发器 + 4 全屏面板；两端同源 fetch JSON-RPC 闭合
- **需求溯源**：六痛点（技能散落 / 误删不可逆 / 升级覆盖定制 / 仓库无账本 / 服务手动拉起 / 冷启动性能债）
- **设计问题九项**（高 2 / 中 4 / 低 3），每项附建议，详见交互页或 dag-data.json

## 目录结构

```
├── dsh-manager-plugin-page.html   # 单页交互 DAG（cytoscape，本地 vendor，离线可用）
├── report.md / report.html        # 分析报告（AI 镜像 / 可读版）
├── 02-analysis/dag-data.json      # 结构化分析数据（5 core + 18 stub + 23 边）
├── 03-vendor/                     # cytoscape + dagre 本地库
└── 01-source/dsh-manager/         # 被分析源码快照（v0.35.6 @ ebbe995）
```
