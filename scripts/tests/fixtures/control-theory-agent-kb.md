# 控制理论 ⊗ Agent 设计知识库

> **版本**：v1.2.0（6 框架 + 14 精装房全景 + 自改造 opencode 变体）｜创建：2026-09-07｜v1.1 扩展：2026-09-08｜v1.2 自改造 opencode 变体专题：2026-09-09
> **定位**：以 Agent 设计构建为业务核心，控制理论作为解决 Agent 工程问题的**技术工具库**引入。
> **核心命题**：把 Agent 当作一架装了传感器、执行器、逻辑决断器的无人机去建模与控制，拒绝把它当成会聊天的搜索引擎。

---

## 快速开始

| 想做什么 | 去哪 |
|---------|------|
| **人类可读入口**（推荐从这里看） | [`index.html`](index.html) |
| 官方 vs 自改造对照页 | [`04-interactive/compare-opencode.html`](04-interactive/compare-opencode.html) |
| 自改造 opencode 画像 | [`04-interactive/case-opencode-custom.html`](04-interactive/case-opencode-custom.html) |
| 精装房全景（14 款产品谱系） | [`04-interactive/premium-map.html`](04-interactive/premium-map.html) |
| 精装房交互 DAG | [`04-interactive/premium-cyto.html`](04-interactive/premium-cyto.html) |
| 五环框架总览 | [`04-interactive/framework.html`](04-interactive/framework.html) |
| AI 检索索引 | [`05-md/00-index.md`](05-md/00-index.md) |
| 31 个控制理论知识点 | [`01-theory/`](01-theory/) |
| 契约（命名/信源/门控规范） | [`00-contract/contract.md`](00-contract/contract.md) |
| 门控脚本 | [`07-checkpoint/kb_gate.py`](07-checkpoint/kb_gate.py) |
| 本次任务留档 | [`archive/0908-精装房Agent全景/`](archive/0908-精装房Agent全景/) |

**本地起服务器跨平台访问**：

```bash
cd 04-interactive && python3 -m http.server 8321
# 浏览器访问 http://localhost:8321/index.html
```

---

## 一、知识库是什么

本知识库系统性地把**控制理论核心思想**（负反馈闭环/状态估计/PID/鲁棒控制/分层控制）深度融入 **Agent 设计与开发**，帮助从业者从「调参工程师」进化为「系统架构师」。

### 五大核心环框架

| 环 | 控制理论对应 | Agent 工程问题 | 章节 |
|----|------------|--------------|------|
| **M 记忆/状态估计** | 状态估计/观测噪声/卡尔曼滤波 | 长上下文取舍、工作记忆蒸馏、观测噪声过滤 | `ch-memory` |
| **P 规划/分层控制** | 分层控制/慢-快双速控制器 | 任务分解、里程碑设定、慢规划器+快执行器 | `ch-planning` |
| **R 反思/反馈闭环** | 反馈闭环/误差收敛/积分环节 | 自我反思、错误回馈、长期偏航补偿 | `ch-reflection` |
| **T 工具调用/执行器** | 执行器/容错/鲁棒性 | 工具调用失败、冗余仲裁、看门狗限幅 | `ch-tool` |
| **E 评估/传感器** | 传感器/验证器/信噪比 | Critic 模块、验证器、反馈信号质量 | `ch-eval` |

> **闭环方向**：E 决定反馈信号质量 → R 决定纠偏量 → P/T 决定轨迹 → M 决定「我以为我在哪」。任一环失效，闭环即破。

### 核心洞察（6 框架对比，主 Agent 终裁）

1. **T 环（执行器）是 6 框架共同的「最强环」**——看门狗/限幅/沙箱是 Agent 工程最成熟环节
2. **E 环（评估）从样板三产品「一致最弱」分化为两派**——hermes/codex 有独立 Critic 体系（E 环强），opencode/dsh/PRIME/claude-code 仍偏弱
3. **各产品最弱环分化**——opencode/dsh/PRIME/claude-code 最弱环=E，hermes/codex 最弱环=P
4. **M 环普遍缺置信度（P 协方差）**——记忆多记事实不记「我有多确定」
5. **装配层可定向补齐内核弱环**——官方 opencode E/R 弱，经自改造（reflection/grill-me/search-worker/门控）E/R 反转，精装度 2.9→3.9（+1.0）

---

## 二、v1.1 精装房全景专题

**核心命题**：声称 ≠ 实际——源码分析能看出真正的一手还是二手。

**四维坐标系**：精装度 0-5（主轴）× 一手/二手（标签）× 4 大类（分组）× 五环定位（控制本质）

### 精装度谱系（14 产品，v2.0 加权模型）

> 评分模型：**硬门槛前置（端到端可跑，0/1）+ 8 维加权（多Agent16/一键部署15/模型14/工作流13/Skill12/沙箱10/MCP10/记忆10）+ 一票否决（声称失实封顶4.0、纯中转封顶3.5）**。
> 详见 [`07-checkpoint/premium-scoring-model.md`](07-checkpoint/premium-scoring-model.md) 与重算矩阵 [`07-checkpoint/premium-score-recompute.md`](07-checkpoint/premium-score-recompute.md)。

| 分层 | 分值 | 产品 |
|------|:---:|------|
| 真·开箱即用 | ≥4.5 | Devin(5.0) / WorkBuddy(4.6) |
| 成品化受限 | 3.5-4.5 | Cursor(4.4) / Dify(4.3) / OpenHands(4.2) / Coze(4.2) / Copilot(4.1) / Windsurf(4.0) / OpenClaude(3.8) / GPT-Researcher(3.7) / CodeWhale(3.5) |
| 需装修/中转 | <3.5 | CrewAI(3.0) / CC-Router(2.1) / QCode(1.4) |
| 技术框架（对照） | 2.5-3 | opencode / dsh / PRIME / hermes / claude-code / codex |

### 三大实证发现

1. **二手被高估**：CC-Router（源码级铁证依赖第三方网关 `@the-next-ai/ai-gateway`）、QCode（官方明示「官方价×服务倍率」）
2. **一手被低估**：CodeWhale（自研 20 个 Rust crate）、OpenClaude（独立 TypeScript 实现）
3. **声称功能不存在**：Windsurf 无「Flows DAG」多 Agent 编排

---

## 三、目录结构

```
0907-控制理论Agent设计知识库/
├── 00-contract/          # 契约（命名/信源分级/L1-L7 门控/精装房专题约定）
├── 01-theory/            # 5 分区理论证据包（31 知识点，≥2 权威源交叉验证）
├── 02-framework/         # 五大核心环映射框架
├── 03-cases/             # 6 框架画像 + 自改造变体（opencode-custom*.md）+ 14 精装房画像（premium-*.md，含证据来源区块）
├── 04-interactive/       # 人类端交互 HTML 集群（36 页）
├── 05-md/                # AI 友好 MD 镜像 + 索引
├── 06-experiments/       # 6 框架标准实验组记录
├── 07-checkpoint/        # 门控脚本 + 实证证据 + 审计报告
├── 08-drawio/            # 五环控制回路图 + 控制概念映射表
├── 09-src-data/          # DAG DATA / KT 详情 / 生成脚本
├── archive/              # 任务留档（0908 精装房专题报告）
├── index.html            # 人类入口
└── README.md             # 本文件
```

> **注**：`05-source/`（第三方源码留档）与 `07-checkpoint/tmp-evidence/`（外部抓取快照）未纳入仓库（体积 475M），见 `.gitignore`；如需可经官方仓库获取。

---

## 四、质量门控（L1-L7）

| 层 | 名称 | 工具 | 本次结果 |
|----|------|------|:---:|
| L1 | 生成时自验证 | py_compile + 样例实跑 | PASS |
| L2 | 全量审计 | 审计脚本 | PASS |
| L3 | 结构层 | `kb_gate.py --layers structure,links,nav` | PASS（139/1564/38 项） |
| L4 | 视觉层 | VLM（vision-worker） | PASS |
| L5 | 渲染层 | `kb_gate.py --layers render` | PASS（canvas 正常） |
| L6 | 覆盖度层 | `kb_gate.py --layers coverage` | PASS |
| L7 | 信源层 | `kb_gate.py --layers sources` | PASS（20/20 画像含证据区块） |

复现命令：

```bash
python3 07-checkpoint/kb_gate.py \
  --root . \
  --layers structure,links,nav,cascade,coverage,sources \
  --nav-source 09-src-data/nav_data.py \
  --exclude tmp-evidence --exclude 05-source --exclude 03-cases/source \
  --nav-exempt 07-checkpoint/report-v1.1.html \
  --content-glob "03-cases/*.md"
```

---

## 五、信源与证据

- **分级体系**：S1 权威一手（官方文档/源码）> S2 权威二手 > S3 社区转引（仅作线索）> S4 一手观察（本库实测）
- **交叉验证**：理论类 ≥2 独立 S1/S2 源；案例类以 S1/S4 为准
- **证据区块**：20 份画像（6 框架 + 14 精装房）均含 `📚 证据来源` 表（SRC 编号 + 级别 + 置信度）
- **实证证据汇总**：`07-checkpoint/premium-evidence.md`、`07-checkpoint/premium-diff-analysis.md`

---

## 六、方法论沉淀

本知识库的建设过程沉淀为一套可复用 skill 集合（`kb-construction`，五类谱系分流 + 公共主干 + L1-L7 门控），已内化至本机 opencode 环境：

- 主入口：`~/.config/opencode/skills/kb-construction/SKILL.md`
- 参考资产：6 个 `reference/*.md`（含 86 个 GitHub 权威仓库实测清单）
- 可执行脚本：5 个 `scripts/*.py`（分块/索引/混合检索/评测/门控）

---

## 七、实验红线（最小必要破坏性范围）

- **原则**：可逆 + 受控故障注入；仅 `/tmp/opencode` 隔离区实机实验 + 源码只读分析
- **禁止**：`rm -rf` 非 `/tmp/opencode` 路径；修改记忆系统文件（MEMORY.md / pending.json）；改真实 API 密钥
- **需前置确认**：首次 `rm`、大范围改造配置、kill 非本实验进程
- 完整三清单见 [`00-contract/contract.md`](00-contract/contract.md) §7

---

## 八、维护与更新

- 本库为长期维护库，随上游产品更新持续维护
- 更新遵循契约 `00-contract/contract.md` 与级联更新方法论（12 项检查表）
- 新增/修改节点后必须回归：生成脚本 + 交互图 DATA + 门控全量验证
- 门控口径统一为 **L1-L7**（见 `07-checkpoint/kb_gate.py`）

---

## 九、许可与引用

本知识库为个人研究成果，欢迎参考。引用实证结论时请保留信源标注（SRC 编号）。

> ⚠️ 所有产品精装度评分基于 2026-09-08 的公开信息与源码分析，产品迭代快，建议定期回归。
