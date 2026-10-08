# zako-mio.github.io

技术知识中枢主页（v2）：**作品集（B）＋ 枢纽聚合（E）** 双主线，全量索引 `zako-mio` 名下已启用 GitHub Pages 的公开项目。

- 站点：**Next.js 15**（App Router，`output: 'export'` **纯静态导出** → `out/`）
- 路由（IA-3）：`/` · `/works` · `/works/<name>` · `/stats` · `/about`
- 数据管道：`scripts/`（Python 标准库，分层：sources / domain / cli）
- 自动更新：GitHub Actions 每日 03:17 UTC + 手动触发

## 为什么是静态导出

部署目标是 GitHub Pages（纯静态托管），因此 **任何 SSR / Route Handler / 服务端运行时特性都不得引入**。
`next.config.mjs` 的 `output: 'export'` 是硬约束，不是可调选项。

## 本地开发

```bash
pnpm install
python3 scripts/cli.py --config site.config.json --out src/data/projects.json   # 或 pnpm fetch
pnpm dev            # http://localhost:4321
pnpm build          # next build -> out/
pnpm preview        # 起静态服务器预览 out/
```

> gh token：`export GH_TOKEN=$(gh auth token)`（提升速率上限，避免未认证 60/h 限制）

## 门控（读真实产物，不读源码自述）

```bash
python3 scripts/validate_catalog.py src/data/projects.json src/data/projects.schema.json
python3 scripts/gate_contrast.py          # 对比度：读 src/app/globals.css 的真实令牌
python3 scripts/smoke_static.py           # 静态导出冒烟：读 out/ 的实产物
python3 scripts/gate_metrics.py           # E 指标口径（G1–G10）：读 src/data/metrics.json ＋ E4 确认登记
python3 scripts/gate_ia_division.py       # 页面分工：读 out/，判「每类内容唯一落点」
python3 scripts/gate_theme_states.py      # 主题三态 × 双模图表同步（防新增主题档时静默失效）
```

> 门控**集合与口径的单一真相源**是 `scripts/gate-manifest.json`（`A8` 硬门保证漏登记即 FAIL）——
> 本节的清单只作导航，⛔ 不写死门控数量（会腐化的字面常量）。

`gate-manifest.json` 在案的每道门控都带 `--selftest`（内置**负向夹具**，用来证明判据不是恒真）：

```bash
python3 scripts/gate_contrast.py --selftest
python3 scripts/smoke_static.py --selftest
python3 scripts/gate_metrics.py --selftest
python3 scripts/gate_ia_division.py --selftest
python3 scripts/gate_theme_states.py --selftest
```

### `scripts/gate_theme_states.py`（`T1`–`T5`）

`/stats` 的图表是**两份**构建期 SVG（浅色帧 `.chart__frame` 默认显示 ／ 深色帧
`.chart__frame--dark` 默认 `display:none`），**换哪一份由 CSS 决定、不由 JS 决定**。
⇒ 新增主题档（改 `THEME_MODES`）或改选择器而**未同步这些规则**时，图表会**静默**停在错误的一份上。
本门控把该同步关系固化为判据：强制档各有对应 `[data-theme='<档>']` 规则（`T1`）、
跟随系统分支存在且以「非强制浅色」限定（`T2`）、默认态基线存在（`T3`）、
`charts.json` 每图 `svg.light`/`svg.dark` 成对非空（`T4`）、产物中双模帧实例成对（`T5`）。

### 图谱分层口径（`scripts/build_topology.mjs`）

对项目公开的 `*-dag.json` 做**构建期 headless 拓扑复算**（cytoscape 只当内核，不做画布），
与项目自称**并陈**。分层口径须与上游一致，否则会把合法图误报成「有环」：

- **不参与分层的边（两类）**：`type_only === true`（TS 类型导入边，类型环合法）；
  `soft === true`（**运行时反馈边**）。⛔ 只排除前者会留下反馈边 ⇒ 残环 ⇒ 误报「19 层不可复算」。
- **方向**：Layer 0 = 基础（被依赖方）⇒ 用「`to -> from`」反转方向做最长路径分层。
- **口径共指纹**：`build_topology.mjs` 把「我方复算 vs 上游自带 `layers` 字段」的逐节点比对
  记入 `analysis.upstream_layer_parity`；`pnpm reverify`（S3）见 `mismatches > 0` 即 FAIL。
  ⇒ 详见 Mission 目录 `ERRATA-batch3-deepseek-acyclic.md`（2026-10-08 勘误）。

## 日常复验（`scripts/reverify.py`）

门控全绿**不等于**交付可信（门控可能本身哑火）。日常复验把「门控之外的复验手法」固化成一个
**可执行、fail-closed** 的入口（**非门控**，不进 `scripts/gate-manifest.json`）：

```bash
pnpm build && pnpm reverify          # = python3 scripts/reverify.py
python3 scripts/reverify.py --skip S2,S5   # 跳过慢/联网段
```

| 段 | 内容 | 为什么 |
|---|---|---|
| `S1` | 清单在案的每道门控跑「本体 ＋ `--selftest`」，rc 必须为 0；并核对「`gate_*.py`/`smoke_*.py` 全部登记」 | 门控与登记义务一起复验 |
| `S2` | `charts` / `topology` 各**两个独立进程**重建，剔除运行时钟字段后逐字节一致；同路径二次运行幂等 | 派生件确定性与幂等（⛔ 同进程二次渲染会 `zr0`→`zr1`，必须跨进程） |
| `S3` | **数字类断言全量对账**（当场重算，⛔ 不复读记录）：跨产物计数一致、`topology↔metrics` 复算、**上游层次口径共指纹**、产物渲染断言 | 数字类断言只扫记录会漏检；口径漂移会静默产生假结论 |
| `S4` | 每道声明 `selftest:true` 的门控，其自检输出**必须含负向夹具触发证据** | 防「门控是恒真/哑火」——自检必须真能 FAIL |
| `S5` | `acceptance_probe`（结构类，须 ALL PASS）＋ `dup_probe`（数值/报告类，只须可跑） | 探针复跑；重合度是**报告项**，⛔ 不判 PASS/FAIL |

> ★ `S3` 的「**上游层次口径共指纹**」是 2026-10-08 勘误后的回归护栏：`build_topology.mjs` 会记录
> `upstream_layer_parity`（我方复算 vs 上游自带 `layers` 字段的逐节点比对），`reverify` 见 `mismatches > 0` 即 FAIL。
> 详见 Mission 目录 `ERRATA-batch3-deepseek-acyclic.md`。

## 信息架构与页面分工

IA-3 五路由，**每页只回答一个问题**，每类内容只有一个落点：

| 路由 | 回答的问题 | 专属内容（唯一落点） |
|---|---|---|
| `/` | 这个人**是谁、做什么、强在哪** | 定位陈述、精选代表作（`overrides.json` 的 `featured`）、**本站做法**（由 `scripts/gate-manifest.json` 派生）、站点分区导航 |
| `/works` | **都有哪些作品** | 全量索引 ＋ 筛选/排序/搜索（筛选态写入地址栏） |
| `/stats` | **数据的规模与口径边界** | 一切聚合数字：计数、规模指标（E）、分布、时间线 |
| `/about` | 这个人**是谁、怎么工作、怎么联系** | 技术画像、工作方式、匿名约定、联系方式 |
| `/works/<name>` | 单个项目的**证据** | 概览、摘要、关联、该项目图谱、入口 |

- 上述分工由 `scripts/gate_ia_division.py` 机检（`A1`–`A9`）：首页**不得**枚举全量作品
  （≤5 项）、**不得**含索引控件 `filterbar`、**不得**出现 `stats__grid` / `about__grid` /
  `contact__list` 三类专属于他页的区块；`A4` 是对照臂（首页 Hero 必须承载定位）；
  `A6`/`A9` 是**防回退棘轮**（首页可见字符；`A9` 额外剥除 `<details>` 折叠内容，
  堵住「把内容全折起来而 `A6` 仍绿」的盲区）——⛔ 二者都**不判"内容够不够"**，观感归人；
  `A7`/`A8` 校验 `scripts/gate-manifest.json` 与 `scripts/` 实际集合一致（**新增门控漏登记即 FAIL**）。

### `scripts/gate-manifest.json`（门控与能力层取用的声明式清单）

首页「本站是怎么做的」区块**由此文件派生渲染**，⛔ 页面不写任何计数（避免会腐化的字面常量）。
新增/移除门控时只改该清单；`A7`/`A8` 会校验「声明的脚本存在」「声明 `selftest: true` 者真的支持
`--selftest`」「`scripts/` 下符合 `gate_*.py` / `smoke_*.py` 命名约定的门控都已登记」。
⇒ ⚠ **命名约定即登记义务**：新门控若不用这两个前缀，`A8` 不会发现它漏登记。
- ⚠ 首页与 `/works` 仍有约 56% 的字面文本块重合，但经逐条核对，其来源**只有两类**：
  精选 3 卡（**包含关系**，有意为之）与全站公共件（导航/页脚）⇒ **零枚举重复**。
  因此字面重合度**只作报告项、不判 PASS/FAIL**（启发式，同义改写不计入）。

## 设计系统约定

- **角色令牌**（`src/app/globals.css` 的 `:root` / `:root[data-theme='dark']`）与
  `fe-starter-kit/tokens/contract.json` 的 11 个 role 同名对齐：`text.primary` / `text.secondary` /
  `text.tertiary` / `link` / `brand.primary` / `border.line` / `border.subtle` / `surface.page` /
  `surface.raised` / `surface.subtle` / `surface.stripe` ⇒ 便于后续新增 binding 时逐角色映射。
- **明暗三态**：`跟随系统`（无属性）/ `[data-theme='light']` / `[data-theme='dark']`。
  ⛔ **不要改用 `light-dark()`**：栈 B/C 的 CSS 管线会把它降级为静态双变量，运行时改
  `color-scheme` 不会重算（`fe-starter-kit/docs/STACK-NOTES.md` 两栈各复现一次）。
  `color-scheme` 由 CSS 选择器分支承担，`data-theme` 由 pre-paint 内联脚本落定。
- **语义 HTML**：卡片取消整卡覆盖层，交互目标是显式链接（键盘 / 屏幕阅读器友好）。
- **背景系统 = 真实公开素材**（第六批）：浅/深各一帧，显隐由**主题选择器**决定
  （`[data-theme]` / `prefers-color-scheme` 决定 `.backdrop__photo--day|--night` 谁 `display:block`），
  非当前主题的一帧 `display:none` ⇒ 浏览器**不会下载**它。⛔ 不要改成「两帧各挂 opacity」。
  - 夜间：ESO `eso0934a`（真实银河，**CC BY 4.0，须署名**，署名在页脚 `footer__credits`）。
  - 日间：`Lofoten, Norway (Unsplash)`（极光天幕，**CC0**）按亮度派生的浅色纱幕
    （暗天空归白 ⇒ 不在浅色页底压出灰幕）。
  - 产物 `public/backdrop/*.webp`（1280/1920/2560 + 一条夜间竖版）由
    `scripts/build_backdrop_assets.py` **幂等**生成（需 Pillow + numpy；原始素材不入仓，脚本头注有直链）。
  - 正文压在照片上 ⇒ **令牌对比度 ≠ 页面对比度**：凡动背景，必须重跑合成后对比度实测
    （批五 `batch5-evidence/contrast_probe.py` 只覆盖浅色；批六
    `batch6-evidence/contrast_probe_theme.py` 覆盖**深浅双主题**）。
- **夜间星野特效（tsparticles，MIT）**：`preset-stars` + 本站覆盖项，**叠加**在银河照片之上。
  懒加载（`next/dynamic({ssr:false})`）⇒ ⛔ 不进首屏 JS（实测 `/` 仍 106 kB，粒子独立分块 105 KB）。
  两条熔断**必须保留**：`prefers-reduced-motion: reduce` 与 `[data-motion='off']` 下**卸载画布**
  （浅色档同理：`display:none` 只是「不显示」，rAF 仍在算）。判据见
  `batch6-evidence/verify_backdrop_fx.py`（含「画布 backing = CSS × DPR」的清晰度机检）。
- **网格/弹性子项必须显式收缩**：`grid-template-columns: 1fr` 与 flex 子项默认 `min-width: auto`
  ⇒ **不会收缩到内容最小宽度以下**。实测：`.detail__main` 漏了这一条，窄屏被构建期 ECharts SVG
  与指标表撑到 653px（视口 390）整页截断。宽内容请放进带 `overflow-x:auto` 的容器
  （`.chart__frame` / `.mtable__scroll`）并给外层 `min-width: 0`。
- **内联 SVG 图件**（`src/components/figures/*`）为**手工定位**（无布局引擎）⇒
  几何缺陷不会自己暴露。判据 `batch6-evidence/verify_svg_layout.py`：
  `S1` 文字压框/压字、`S2` 箭头落点（矩形切边合法／圆形须留 ≥4px 净距），带 `--selftest` 负向夹具。
  ⚠ **声明的不覆盖面**：`circle`/`ellipse`/`path` 不判（圆的外接正方形会把「环内中央的文字」
  误报为重叠）。改动图件后必须重跑该判据。

## 已知取舍

- 静态导出 + 客户端筛选 ⇒ 首屏共享 JS 约 102 KB（React 运行时基线）。相比 v1 的 Astro（零 JS 基线）
  是本次换栈明确接受的成本；换来的是完整 React 生态的交互上限。

## 留档

架构决策（ADR-001）与选型矩阵见 Mission 目录 `1008-个人主页深化改革/`。
