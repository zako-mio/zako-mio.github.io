# zako-mio.github.io

技术知识中枢主页（v2）：**作品集（B）＋ 枢纽聚合（E）** 双主线，全量索引 `zako-mio` 名下已启用 GitHub Pages 的公开项目。

- 站点：**Next.js 15**（App Router，`output: 'export'` **纯静态导出** → `out/`）
- 路由（IA-3）：`/` · `/works` · `/works/<name>` · `/stats` · `/about`
- 数据管道：`scripts/`（Python 标准库，分层：sources / domain / cli）
- 自动更新：GitHub Actions 每日 03:17 UTC + 手动触发（含**浏览器层判据**硬阻，见 `scripts/probes/`）

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
python3 scripts/gate_interaction_surface.py  # 交互作用面：悬停反馈面 ≡ 点击热区（关系型判据）
python3 scripts/gate_background_salience.py  # 背景显著性：背景层结构护栏 ＋ 显著性报告项
python3 scripts/gate_motion_budget.py        # 动效预算：进场/常驻动效的失控守卫（四项上界）
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
python3 scripts/gate_interaction_surface.py --selftest
python3 scripts/gate_background_salience.py --selftest
python3 scripts/gate_motion_budget.py --selftest
```

> ★ **阈值型判据有结构性盲区**：「悬停有反馈但点击无响应」「背景抢焦点」这类缺陷是
> **关系型 / 层级型**的，对比度、溢出、包体这类**阈值型**门控看不见它们。
> ⇒ 第七批补的这两道门控专门管「关系」（作用面之间的对齐），⛔ 不要用调阈值的方式去凑。

### `scripts/gate_theme_states.py`（`T1`–`T5`）

`/stats` 的图表是**两份**构建期 SVG（浅色帧 `.chart__frame` 默认显示 ／ 深色帧
`.chart__frame--dark` 默认 `display:none`），**换哪一份由 CSS 决定、不由 JS 决定**。
⇒ 新增主题档（改 `THEME_MODES`）或改选择器而**未同步这些规则**时，图表会**静默**停在错误的一份上。
本门控把该同步关系固化为判据：强制档各有对应 `[data-theme='<档>']` 规则（`T1`）、
跟随系统分支存在且以「非强制浅色」限定（`T2`）、默认态基线存在（`T3`）、
`charts.json` 每图 `svg.light`/`svg.dark` 成对非空（`T4`）、产物中双模帧实例成对（`T5`）。

### `scripts/gate_interaction_surface.py`（交互作用面：反馈面 ≡ 热区）

**要解决的问题**：给「非交互区块」加悬停动效＝**假可供性** —— 用户会读作「这里能点」。
实测反例（批七取证）：整卡有抬起/描边/指针光斑，但仅标题链接与页脚外链可点，
**coverage = 0.131**（87% 的反馈面是死区）；分区项 `.related__item` 为 **0.194**。

本门控把「反馈面 ≡ 热区」固化为**契约**，静态可跑（CI 无需浏览器）：

| 判据 | 内容 |
|---|---|
| `C1` 双向闭合 | `globals.css` 的 `:hover`/`:focus-within` 规则集合 ⟺ `scripts/interaction-surfaces.json`（漏登记 / 幽灵登记 ⇒ FAIL） |
| `C2` 空集守卫 | 每条登记的「去伪类基选择器」必须在 **out/ 全量产物**里命中 ≥1（防登记表静默腐化） |
| `C3` 覆盖率契约 | `kind ∈ {self, container}` 必须声明 `coverage_min ≥ 0.98`；已知缺陷可登记为 `status: rework`（须带 `deadzone_note` + `expires_at`，只 WARN）。★ 批十三新增 `decor` ⇒ `C3`/`C4` **不适用**（见下） |
| `C4` 焦点等价 | 有 hover 就必须有焦点等价面（WCAG 2.2 SC 1.4.13） |
| `C5` 装饰层前提 | ★ 批十三：`data-spotlight` 宿主**不得自带** `.x::before`（与 `[data-spotlight]::before` 特异性相同 ⇒ 高光层会**静默吃掉**宿主的装饰伪元素）。⇒ 约定＝宿主把 `::before` 让给高光层，自有装饰改用 `::after`／子元素（落地：`.hero__eyebrow` 的状态点、`.threads--rail` 的强调轨）。⛔ `*::before` 这类无类/标签锚点的规则不判（第一版判据曾因此把 384 个元素全判 FAIL） |

**对象必须分类**（第一版判据在此踩坑）：`self`（元素自身即交互目标）／
`descendant`（某交互目标的后代装饰件，coverage=0 属正常，判据上溯最近交互祖先）／
`container`（非交互容器 —— **只有这一类**的「反馈面 > 热区」才是真缺陷）／
★ `decor`（**装饰性反射面**，第十三批新增 —— 指针跟随高光；它**不暗示可点击**，
故「反馈面 ≡ 热区」的覆盖率契约对它**不成立**）。

> ★★ **`decor` 为什么必须新开一类**（第十三批 · **用户裁决** 2026-10-10）：
> 用户裁决 V1 要求「所有带边框/圆角容器**统一**」加指针特效，而本站既有判据要求
> `container` 的「反馈面 ≡ 热区」⇒ **两者对无热区的纯展示件（`.figure` / `.chart__frame` /
> `.hero__map`）互锁**：按 V1 施工，那些件必然被判「假可供性」FAIL。
> 裁决走「**新增 kind ＋ 更严替代判据**」（⛔ 不是放宽——放宽的唯一合法路径是用户裁决＋更严替代）：
> - 豁免：`C3` 覆盖率、`C4` 焦点等价（装饰层无「键盘看不到鼠标看到的反馈」这一信息等价问题）；
> - **不放宽**：`C1` 双向闭合 / `C2` 空集守卫照旧（装饰面同样不得漏登记、不得腐化）；
> - **替代判据**（`scripts/probes/surface_hit_probe.py` 的 `decor` 分支）：
>   `D1` `cursor` 不得为 `pointer`（装饰面 ⛔ 不得用光标暗示可点击）；
>   `D2` 面内（或元素自身）**含交互目标** ⇒ **回退**按 `self`/`container` 口径判覆盖率。
> ⇒ `D2` 是「decor 不得成为逃生门」的机检保证：统一选择器 `[data-spotlight]` 下
> `.card`（经拉伸层可点）与 `.figure`（不可点）**按实例分别判**，前者仍须 ≥0.98
> ⇒ **统一选择器不降低既有件的严格度**。
> 两边判据（门控 ＋ 探针）**同批改**且各带 `--selftest` 负向夹具（含「decor 面内含交互目标
> 必须回退」与「产物无 `[data-spotlight]` ⇒ 属性探针零命中」两条）。

⚠ **声明的不覆盖面**：真实覆盖率（面积比）须浏览器实测，本门控只校验**契约是否被声明且未腐化**；
「每个可点目标是否都有 hover 反馈」（欠反馈方向）静态亦不可判。两者由**行为口径**探针承担：
历史件 `batch7-evidence/audit_site.py`（几何口径）／活件 `scripts/probes/surface_hit_probe.py`
（**已是 CI runtime 硬阻**，见下文 `scripts/probes/` 一节）。

> ★★ **几何口径 ≠ 行为口径**（第八批实测）：`batch7-evidence/audit_site.py` 的 coverage 用
> 「交互后代的**几何盒**面积」当热区 ⇒ 对**伪元素命中区**（stretched link）**结构性失明**：
> 同一张卡，几何口径仍读 **0.131**，行为口径读 **1.0**（两者都对——量的不是同一个事实）。
> ⇒ 第八批补 **行为口径**仪器（归档件 `batch8-evidence/audit_surface_hit.py`；CI 活件
> `scripts/probes/surface_hit_probe.py`）：面内布点 → `document.elementFromPoint()`
> → 命中的可交互祖先是否**在该反馈面之内**。带负向夹具（含「同容器 + stretched ::after」对照臂，
> 证明它**能看见**几何口径看不见的机制）与「整轮无可量测项即 FAIL」的逃亡门守卫。
> ⛔ 两口径不可互换，任何一处改口径前先问「我在量哪个事实」。

### `scripts/gate_background_salience.py`（背景显著性）

对比度门控管的是**令牌对**（≥4.5:1），管不了「背景是否抢焦点」——后者是**显著性/层级**问题。
本门控把强度分成两档，⛔ **不得混用**：

- **护栏（fail-closed）**：`B1` `.backdrop` 必须 `pointer-events:none` 且 `z-index < 0`；
  `B2` 全量产物的 `.backdrop` 子树内不得含可聚焦元素；
  `B3` 动效熔断必须是**全局**（`reduced-motion` 与 `[data-motion='off']` 下各有 `*` 级 animation 压制）
  且不得被 `animation-duration: … !important` 绕过。
- **报告项（⛔ 不判阈值）**：背景层数、运动层数、纱幕档位、照片 opacity/filter。
  （★ 批十七：原「网格遮罩峰值」报告项随 `.backdrop__grid` 移除而删除。）
  ⇒ 依 `criterion-design-validation` 的口径：**代理指标不得接自动回写**；
  「背景是否抢焦点」的显著性尚未验证与目标同向，只出读数供人审阅。

### `scripts/gate_motion_budget.py`（动效预算）

「动效预算」不是对比度/包体那样的**贴合式**阈值，而是**数量级失控守卫**：防止某次改版静默引入
「一页上百个进场元素」「错峰三秒」「常驻动画几十个」这类总时长/总开销失控。⛔ 它**不判**动效好不好看
（观感归人），也不判「够不够」——与 `A6`/`A9` 棘轮同一取向。四项**上界**：

| 判据 | 量 | 基线（`as_of=2026-10-09`） | 阈值 |
|---|---|---|---|
| `M1` | 单页 `[data-reveal]` 实例数 | 8（`/about`） | ≤ 32 |
| `M2` | **进场完成时间** = 最大错峰（`--i×70ms`）＋ 最长 `--dur-*` | 990ms | ≤ 兜底窗口（1800ms） |
| `M3` | `--dur-*` 设计令牌之和 | 1.79s | ≤ 3.6s |
| `M4` | 常驻（`infinite`）动画的元素数 | 6（`/`） | ≤ 12 |

★ **阈值推导不许由规模直觉**（`b89`）：`M1/M3/M4` ＝「实测基线 × 声明余量」（×4 / ×2 / ×2，理由是
「正常内容增删不触发、数量级失控才触发」）；`M2` 的上界**由项目常量推导** —— 取
`MOTION_INIT_SCRIPT` 的 **1800ms 兜底窗口**（运行时未接管就把全部 `[data-reveal]` 一次摊平），
语义是「进场动效应当在兜底触发前结束」；该数字**当场从 `src/lib/motion.ts` 解析**，⛔ 不写第二处字面量。
⚠ **作用面声明**：`M2` 只量**进场**类错峰；CSS 里另一族 `animation-delay`（流星 2.5/9/16s 等
**常驻环境**动画）**不是进场延迟**，只作报告项（首版判据正是错把 16s 流星当「错峰」而假 FAIL）。
⚠ **不判面**：本门控⛔ 不度量真实帧率/掉帧/耗电（须真机）。

### `scripts/probes/`（浏览器层判据：CI 的 runtime 硬阻）

上面那些门控都**只跑 python3**。有七类缺陷只有真浏览器能看见（图件几何、合成后对比度、
悬停反馈面 ≡ 热区、`:hover` 门控、**进场可见性 × 进入路径**、**术语解释层的 hover/focus/Esc**、
**无障碍（axe-core：对比度/标题层级/名称/ARIA…）**），
长期是**提示词级**（写进文档、靠人记着跑）。
现把活件收进 `scripts/probes/`，CI 里装 playwright ＋ 起一次静态服务后**逐条硬阻**（失败即阻断部署）：

| 探针 | 判据 | 需浏览器 |
|---|---|---|
| `check_provenance.py` | 探针登记完整性（漏登记 / 幽灵登记 / 空集 fail-closed，带 `--selftest`） | 否 |
| `check_ci_manifest.py` | **CI 步骤 ↔ 登记集合一致性**（`E1`：门控/探针**双向** fail-closed —— 登记⇒必须进 CI，CI 里出现的 `gate_*`/`smoke_*`/`*_probe.py`⇒必须登记；⛔ 不设白名单，带 `--selftest`） | 否 |
| `hover_gating_probe.py` | 产物 CSS 每条 `:hover` 都在 `@media (hover:hover)` 内 ＋ 源/产物集合一致（带 `--selftest`） | 否 |
| `svg_layout_probe.py` | `S1` 文字压框/压字、`S2` 箭头落点（带 `--selftest` 负向夹具） | 是 |
| `contrast_theme_probe.py` | 合成后对比度（深浅双主题 × 两宽度，取最坏像素；带 `--selftest`） | 是 |
| `surface_hit_probe.py` | 行为口径「反馈面 ≡ 热区」覆盖率（对照臂 ＋ 逃亡门守卫；带 `--selftest`） | 是 |
| `reveal_nav_probe.py` | **进入路径无关性**：同一路由的 `[data-reveal]` 可见终态，整页加载臂 ≡ 客户端 `<Link>` 导航臂（带 `--selftest`） | 是 |
| `hero_hit_probe.py` | **Hero 交互保护**（第十三批 W1）：`.hero` 内每个可交互件的中心命中不被打断 ＋ `.hero__map` 不叠热区 ＋ 断点一致 ＋ 图件自身可被命中。★ 十七批（W4-②）两处**作用面收窄**（⛔ 不是放宽）：① `H1` 只判**已渲染**（零尺寸＝未渲染 ⇒ 跳过；`<1024px` 档图件 `display:none`，其内链接 rect 为 0×0，否则中心 (0,0) 会被误判遮挡）；② `H2` 不把**图件内部**的交互件算作「被图件压住」（判据面＝被判对象）——⛔ 二者都**净增**了被检对象（图内 3 个链接仍逐件受 H1 管）（带 `--selftest`） | 是 |
| `term_layer_probe.py` | **术语解释层**（第十四批 W2）：`T1` 静止态隐藏 · `T2` hover 展开 · `T3` 键盘 focus 展开（WCAG 1.4.13）· `T4` Esc 关闭 · `T5` `aria-describedby`→`role=tooltip` 关联可达 · `T6` **无 JS 可读**（直读原始 HTML，不经浏览器）· `T7` **浮层不被 `overflow` 容器裁剪**（★ 十六批 W4/C3：**逐件**「面板内·裁剪框外·视口内」命中测试；`not-open` 亦计 FAIL，⛔ 不许静默跳过）（带 `--selftest`） | 是 |
| `axe_a11y_probe.py` | **无障碍自动化审查**（第十五批 B2）：axe-core 4.14.0（vendored，`vendor/axe.min.js`）注入渲染页跑 `axe.run`；规则白名单＝WCAG 2.1/2.2 A/AA ＋ best-practice（含 `heading-order` 这类既有判据都没在看的类）；双主题 × 5 路由；豁免须**带理由且真命中**（⛔ 防静默过期）；`A4` 非空守卫；带 `--selftest`（对照臂＋负向臂） | 是 |
| `acceptance_probe.py` | **页面分工结构类**（第三批）：`A1` 首页枚举数 ≤5 · `A2` 首页无索引控件 · `A3` 首页无他页专属区块 · `A4` 对照臂 · `A5` 联系区块唯一落点（结构类，须 **ALL PASS** 才 rc=0；带 `--selftest`） | 否 |
| `dup_probe.py` | **页间内容重复度**（第三批）：块级重合矩阵 ＋ 关键元素跨页计数（数值/**报告类**，⛔ 不判 PASS/FAIL ⇒ 无 `--selftest`） | 否 |

- 依赖声明在 `scripts/probes/requirements-probes.txt`（playwright 1.63.0 / pillow 12.3.0）；
  CI 的浏览器缓存键由 `hashFiles()` 从该文件派生，⛔ 不写第二处版本字面量。
  ⚠ 探针层的**前端资产**（`axe-core`）另 pin 于 `scripts/probes/vendor/`（含版本/许可/sha256，见其 README）。
- **十条探针**在 CI 里跑（7 条需静态服务/浏览器 ＋ `hover_gating` 静态解析 ＋ `acceptance_probe` 结构类 ＋ `dup_probe` 报告类）；
  除 `dup_probe`（报告类，无 `--selftest`）外均**连 `--selftest` 一起跑**（判据必须能 FAIL，否则是哑火门控）。
  ⚠ `check_provenance.py` / `check_ci_manifest.py` 是**机检**（不进 `PROVENANCE.json` 的探针表，不在此计数）。
- 基址由 `SITE_BASE` / `--base` 给出（缺省 `127.0.0.1:4399`）；缺 `out/` 时 `hover_gating_probe`
  以 **rc=2** 退「用法错误」（⛔ 不读成判据 FAIL）。
- ★ **来源登记**：`svg_layout` / `contrast_theme` / `surface_hit` / `hover_gating` 四个是 Mission
  归档件的**活件副本**（`PROVENANCE.json` 记 `archive_source` ＋ `source_sha256` ＋ 漂移方向：
  活件可演进、归档件冻结 ⛔ 不追改）；`reveal_nav_probe.py`（第十二批）、
  `hero_hit_probe.py`（第十三批）、`term_layer_probe.py`（第十四批）与
  `axe_a11y_probe.py`（第十五批，另 vendor `axe-core@4.14.0` 于 `vendor/`）是**仓库原生**。
  `check_provenance.py` 保证「目录里的每个 `*_probe.py` 都已登记」—— ⛔ 新增探针必须**同批登记**，
  否则 fail-closed。（同目录 `acceptance_probe.py` / `dup_probe.py` 亦为 `origin: repo-native`。）
- ⛔ 这些活件**不进 `gate-manifest.json`**（命名不为 `gate_`/`smoke_` 前缀 ⇒ 不触发 `A8` 登记义务，
  也就不会派生渲染进首页）；它们由 CI workflow 直接调用。⚠ **workflow 步骤是逐条列举的 ⇒
  新探针必须同批改 `.github/workflows/update-hub.yml`**（「已登记」≠「已进 CI」）——
  该义务**已由 `check_ci_manifest.py` 的 `E1` 做成 fail-closed**（登记 ⇒ 必须进 CI，双向；⛔ 不设白名单）。


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
| `/` | 这个人**是谁、做什么、强在哪** | 定位陈述、**首屏定位图**（`HeroPositionMap`，第八批）、精选代表作（`overrides.json` 的 `featured`）、**本站做法**（由 `scripts/gate-manifest.json` 派生）、站点分区导航 |
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

- **首屏右区 = 定位图（第八批 · 裁决② 的 V3 方案）**：`src/components/figures/HeroPositionMap.tsx`。
  旧件 `HeroFigure` 是 `aria-hidden` 的纯装饰星座（不承载信息；夜间该区高亮像素占比 0.000）；
  本件把 Hero 那句话的**结构**画出来（复合背景 → 核心动作 → 三个聚焦方向），于是首屏最大的
  视觉权重承载与首页职能自洽的内容。三条纪律：
  ① **撤 `aria-hidden`**，改 `role="img"` ＋ `<title>`/`<desc>` 给等价文本（⛔ 不得对承载信息的
     可见内容用 `aria-hidden`）；② ⛔ 不引入 `/stats` 的聚合数字与 `/works` 的作品枚举 ——
     标签只取自定位陈述与 `PROFILE_FOCUS`（它是**图形化**，不是第二处正文）；
  ③ `<1024px` 隐藏**不造成信息丢失**：同一份内容在同页 Hero 标语里以文字存在。
  ⚠ **正文列必须给右区让位**：`.hero__inner > *` 的 `max-inline-size` 由 `--hero-map-w`
  派生（同一令牌，⛔ 不写第二处魔法数字）—— 否则标语首行会压到图件 chip 上（实测 47–110px）。
   ⚠ 标签用**带底色的 chip**：连接线画在其下层不穿字（判据 S1），且文字对比度 ≥15.9（不受背景细节影响）。
  ★ **十七批 W4-②（用户 2026-10-11 裁决「全 B」）：三个聚焦方向＝真链接** ——
  点按到 `/works?domain=…` 按对应方向筛选（映射是**人工声明**在 `profile.ts` 的 `PROFILE_FOCUS_FILTERS`，
  ⛔ 不是推断：`AI Agent 工程→agent-engineering` / `机器学习建模→llm` / `运筹优化→algorithms`；
  ⚠ 第二个是本表**最弱的一环**，靠「大模型是机器学习方向的当前落地形态」成立，用户已知悉）。
  · **`role="img"` → `role="group"`**：`role="img"` 会把子树**压平**，与「方向可点」结构上不相容；
    改后内部文本自然可读，`<desc>` 只讲「怎么读/能做什么」（⛔ 不再复述节点文字）。
  · **`<a>` 只包 chip、⛔ 不包连接线**：`hero_hit_probe` 的 `H1` 判「可交互件的**几何中心**必须命中回
    自己或其后代」，而 `union(线, chip)` 的包围盒中心落在**空隙**里 ⇒ 包线会直接触发 H1 假 FAIL。
  · **连接线高亮走委托 ＋ `data-hl`**（`MotionRuntime`），⛔ 不用 CSS `:hover` 规则：线与节点分属两个 `<g>`，
    CSS 关联要**逐条写 N 条规则**，而那些选择器会落进 `interaction-surfaces.json` 并按**容器口径**判覆盖率
    （细斜线命中率必为 0）⇒ 假 FAIL。
  · **`<a>` 必须显式 `pointer-events: auto`**：`.hero__map__svg` 是 `pointer-events: none`（W1 约定），
    不在链接上重新启用就是**结构性哑火**（点不动）。
  · 同批**移除** wrapper 的 `data-spotlight="soft"` —— 理由见上文「排除项」③（判据判出的假可供性）。
- **进场动效走独立 `translate` 属性（第八批 · 既有缺陷修复）**：`[data-reveal]` 的进场位移原本用
  `transform`，而 `[data-reveal].is-in { transform: none }` 的特异性 (0,3,1) 会连锁压过三处：
  ① `.card:hover { transform: translateY(-3px) }` ⇒ 首页精选卡**从不抬起**（`/works` 却抬起）；
  ② `.card { transition: … }` ⇒ 首页卡片的描边/阴影 hover **一直是瞬变**；
  ③ `.hero__figure { transform: translateY(-50%) }` ⇒ 右区图件**下坠半个身位**
  （实测非 reduced-motion 下 `top=239` 而应为 `59`，一半溢出 Hero ——**线上一直如此**）。
  ⇒ 现改为：进场用 `@keyframes`（**不再声明 `transition`**）＋ 位移/居中走独立 `translate` 属性，
  三者互不竞争。⛔ 不要用「抬高特异性」绕过 —— 那是把渲染顺序问题伪装成权重问题。
- **进场的「接管作用面」必须持续跟随 DOM（第十二批 · 缺陷修复）**：`MotionRuntime` 挂在**根布局**上，
  App Router 的 layout **跨客户端路由常驻**，而 `useEffect(…, [])` 只跑一次 ⇒ 首次扫描之后
  新挂载的 `[data-reveal]` 无人 observe，永远停在隐藏态。用户可见症状＝**动效开时「切回首页 /
  进关于页 ⇒ 内容消失」**（实测：客户端导航后 `/about` 8 个 section、`/` 的 `#featured` 等全为
  `opacity:0 / is-in:false`）。⇒ 现由 `MutationObserver`（只盯 `childList`，⛔ 不盯 `attributes`，
  否则自触发成死循环）**持续接管**新节点，并由 `reveal_nav_probe.py` 把「进入路径无关性」
  升为 CI 硬阻。⛔ 不要退回「挂载时扫描一次」或「`nodes.length === 0` 提前 return」
  （`/works` 没有 `[data-reveal]`，提前 return 会让「从 `/works` 回首页」这一半缺陷重现）。
  ⚠ 连带订正：`ProjectCard` 头注里「动态重渲染的卡片不得用 `data-reveal`」的**根因**已消失，
  但该参数**仍保持 opt-in**（`/works` 筛选器反复重渲染会让卡片重播进场动画）。

- **角色令牌**（`src/app/globals.css` 的 `:root` / `:root[data-theme='dark']`）与
  `fe-starter-kit/tokens/contract.json` 的 11 个 role 同名对齐：`text.primary` / `text.secondary` /
  `text.tertiary` / `link` / `brand.primary` / `border.line` / `border.subtle` / `surface.page` /
  `surface.raised` / `surface.subtle` / `surface.stripe` ⇒ 便于后续新增 binding 时逐角色映射。
- **明暗三态**：`跟随系统`（无属性）/ `[data-theme='light']` / `[data-theme='dark']`。
  ⛔ **不要改用 `light-dark()`**：栈 B/C 的 CSS 管线会把它降级为静态双变量，运行时改
  `color-scheme` 不会重算（`fe-starter-kit/docs/STACK-NOTES.md` 两栈各复现一次）。
  `color-scheme` 由 CSS 选择器分支承担，`data-theme` 由 pre-paint 内联脚本落定。
- **卡片 = 整卡可点 ＋ 页脚外链按钮化**（第八批按用户裁决①落地；**有意反转**批三「取消整卡 `::after`」的决定）：
  主链接用 **stretched link**（`.card__title a::after{position:absolute;inset:0;z-index:1}`）铺满整卡
  ⇒ 反馈面（整卡）≡ 热区；页脚外链改为显式次级按钮（复用 `.button .button--small`）并
  `position:relative;z-index:2` **抬升到拉伸层之上**（⛔ 不抬就会被盖住 ⇒ 外链变死区，
  这是 Bootstrap `stretched-link` 官方点名的配套要求）。`.related__item` 同理（`.related__link::after`）。
  ⚠ 陷阱：祖先带 `transform` / `perspective` / `filter` / `will-change` 会成为新的 containing block
  （拉伸层只覆盖到它）；⛔ 也不要给链接自身加 `position: relative`（拉伸层会缩回链接自己的盒子）。
  ⚠ **既定代价（如实登记）**：卡片内**非交互**正文落在拉伸层之下 ⇒ 文字不可选中、原生 `title` 不触发；
  ⛔ 不得用「把非交互元素也抬升」来绕 —— 那会在热区里重新挖出空洞（官方点名的反模式）。
  ⇒ 机检：`smoke_static.py` 的 **S9**（拉伸层与嵌套抬升必须**成对**，任一侧缺失或抬升不足即 FAIL）。
- **交互状态一律包在 `@media (hover: hover)` 里**（第八批）：`:hover` 在触屏上不可靠且会「粘滞」，
  且内容不得只能靠 hover 才可达。`:focus-within` / `:focus-visible` 等价面 ⛔ **不进**该门控
  （键盘与辅助技术在任何输入设备上都必须看得到反馈）。
  普通文本链接由站内默认态 `a:hover` 覆盖（正文/面包屑/说明/`.nav__brand` 等；
  其特异性 (0,1,1) **低于**所有组件态 ⇒ 组件外观不会被它改掉）；
  ⚠ `.skip-link` 例外：它的底色就是 `--brand-primary`，继承默认强调色会变成同色不可读 ⇒ 显式收回本色。
- **交互状态令牌（批七）**：`:root` 的 `--state-hover-accent` / `--state-hover-surface` 是**语义别名**
  （`var()` 指向既有角色令牌，⛔ 不引入新色值、⛔ 不绕过主题）。新增可交互件只引用这两个语义令牌，
  ⛔ 不要各处再写 `var(--brand-primary)` —— 「同一件事有 7 个副本」正是先前漂移的成因。
- **背景系统 = 真实公开素材**（第六批）：浅/深各一帧，显隐由**主题选择器**决定
  （`[data-theme]` / `prefers-color-scheme` 决定 `.backdrop__photo--day|--night` 谁 `display:block`），
  非当前主题的一帧 `display:none` ⇒ 浏览器**不会下载**它。⛔ 不要改成「两帧各挂 opacity」。
  - 夜间：ESO `eso0934a`（真实银河，**CC BY 4.0，须署名**，署名在页脚 `footer__credits`）。
  - 日间：`Lofoten, Norway (Unsplash)`（极光天幕，**CC0**）按亮度派生的浅色纱幕
    （暗天空归白 ⇒ 不在浅色页底压出灰幕）。
  - 产物 `public/backdrop/*.webp`（1280/1920/2560 + 一条夜间竖版）由
    `scripts/build_backdrop_assets.py` **幂等**生成（需 Pillow + numpy；原始素材不入仓，脚本头注有直链）。
  - 正文压在照片上 ⇒ **令牌对比度 ≠ 页面对比度**：凡动背景，必须重跑合成后对比度实测
    （批五 `batch5-evidence/contrast_probe.py` 只覆盖浅色；**深浅双主题**版＝活件
    `scripts/probes/contrast_theme_probe.py`，归档件 `batch6-evidence/contrast_probe_theme.py`）。
- **背景分区分级（第八批 · 裁决③）**：只在**非阅读带**保留强细节，正文带用**局部 scrim**
  （`.backdrop__scrim`，夹在纱幕之后、运动层之前；★ 批十七前它夹在网格之后，网格层已移除）。阅读带边界由**布局派生令牌**给出
  （`--backdrop-reading-top` / `--backdrop-reading-left`：窄屏上边界＝导航高、宽屏左边界＝`--rail-w`），
  ⛔ 不写死像素。★ 为什么不是「横向分列」：1440px 下两侧 gutter 各仅 ~34px（实测），
  「两侧留细节」**没有可用的面** ⇒ 分区只能落在真实存在的页顶带与左栏带。
  ⛔ 它是**加法层**：原 `.backdrop__veil` 一格不改 ⇒ 非阅读带细节原样保留、合成对比度只增不减。
  ⛔ 本轮**不动**照片 `filter`（属裁决里**未采纳**的独立提案，可重提）。
  ★ 批十七：细网格底（原 `.backdrop__grid`）已按 AI 味裁决 V-A4 整体移除。
- **指针光斑（第八批 · 裁决④ T1；★ 批十一 F-d1 反转输入面）**：`.backdrop__glow` —— **主题无关**的交互通道
  （现状粒子交互「仅夜间 ＋ 不可发现」，光斑补的是对称性与可发现性）。三条护栏：
  ① **输入面**：`(hover:hover) and (pointer:fine)` **或** `(pointer: coarse)` 下 `display:block`。
     ⚠ **批十一有意反转**了批八的「触屏不启用」：批十为消除手机卡顿关掉了星野 `grab`，触屏于是没有触摸反馈；
     用户裁决「换成更流畅的动画」⇒ 触屏也用这层**合成层**光斑（⛔ 不回 canvas 重绘）。
     触屏坐标由 `MotionRuntime` 额外绑的 `touchstart`/`touchmove` 写入（`touchend`/`touchcancel` 移除
     `data-pointer` ⇒ 淡出）；⛔ 卡片光斑（`--mx/--my`）仍只在精确指针路径。
  ② **幅度受限是结构性的**：本层夹在「照片之上、纱幕/scrim 之下」
     ⇒ 光斑永远不可能比照片更亮地照到文字层（实测对正文脚下亮度影响 ≤ ±3/255）。
  ③ 靠 `transform: translate3d()` 随指针移动（合成层，⛔ 不全屏重绘）；
     变量写在光斑元素自身（⛔ 不写 `:root`，那会让整棵树重算样式）。
     `--pointer-x/--pointer-y` 由 `MotionRuntime` 的**同一个**委托 listener 写入（⛔ 不新增监听器）。
  熔断：`prefers-reduced-motion: reduce` 与 `[data-motion='off']` 下 `display:none`
  （前者以 `:not([data-motion='on'])` 限定 ⇒「动效开」可覆盖 OS）。
- **元素级指针高光（第十三批 W1 · 统一约定 `[data-spotlight]`）**：批八起的「卡片指针跟随光斑」
  此前**写死** `.card::before` ＋ `closest('.card')`；批十三把它抽成**全站统一约定**：
  - **宿主**：任何**已定位**（`position != static`）的 HTML 元素挂 `data-spotlight="base|soft|micro"`；
    强度分层由 `--spotlight-radius` / `--spotlight-opacity` 承担（四档；`base` 即无值的默认档）：
    `base` 320px/1 · `soft` 240px/0.55 · `micro` 120px/0.45 ·（`strong` 440px/1，保留未用）。
    档位口径＝**元素尺度 ＋ 是否已有自身反馈**（已有反馈的件取更低档，⛔ 避免与既有 affordance
    叠成双重信号）。⛔ 新增档须同步 `scripts/interaction-surfaces.json` 与探针白名单。
  - **本轮作用面（§4-W1 表全量接入）**：`base`＝`.card` / `.figure` / `.chart__frame` / `.threads`；
    `soft`＝`.metrics__item` / `.related__item`(+`.directory__item`) /
    `.contact__link` / `.disclosure`；`micro`＝`li.chip` / `span.chip` / `.hero__eyebrow`。
    （★ 十七批把 `.hero__map` 从 `soft` 移出 —— 见下「排除项」③。）
  - ⛔ **排除项（三条，均有依据而非遗漏）**：
    ① **控件**（`.button` / `.theme-toggle` / `.motion-toggle` / `button.chip`）——V1 口径「控件非容器」；
    ② **`.mtable__scroll`** —— 宽表内仅「来源」列有少量链接，`surface_hit_probe` 实测覆盖率
    **0.05（28/484）** ⇒ 按本站判据＝**错位（含死区）**，且按 **D2** 它不能走 `decor` 豁免
    ⇒ 规则一致的处置是**不挂**（⛔ 不是放宽 D2）。
    ③ **`.hero__map`**（★ 十七批 W4-②，**同一处置的第二个实例**）—— 批十三 W1 曾为它专门加 HTML wrapper
    承接整图高光；但十七批让它**部分可点**（三个聚焦方向＝链接）后，该高光的反馈面＝**整块图**
    （boxArea 151200）而热区只有 3 个 chip ⇒ `surface_hit_probe` 实测覆盖率 **0.074（9/121）**
    ⇒ 与 ② 完全同规：**不挂**（⛔ 不是放宽 D2，⛔ 不是给这一个实例开豁免）。
    ⚠ 代价如实登记：**图件不再有指针跟随高光**（W1 那一项对它失效）；chip 自身仍有 hover/focus 反馈。
    ⛔ 若要恢复整图高光，必须同时让**整块图**成为真交互面 —— 否则判据必再 FAIL。
  - **JS**：`MotionRuntime` 里**仍是同一个委托 listener**（`closest('[data-spotlight]')`、`passive: true`、
    ⛔ 不逐件加监听器）。`closest()` 能**上溯** ⇒ SVG 子形状作 `event.target` 时也能找到 HTML 宿主。
  - **CSS**：`[data-spotlight]::before` 通用规则。★ **层叠位置＝内容之下**（批十四 W1c 落地用户裁决 V7）：
    `[data-spotlight]{isolation:isolate}` ＋ `[data-spotlight]::before{z-index:-1}` —— 宿主成为独立层叠上下文，
    高光排在「宿主背景之上、静态内容之下」。★ 层叠位置经**像素实测**确认（⛔ 不是靠绘制顺序推断，
    第一版文档在这里写错过）：取图注文字条的**不透明字形核心像素**，字形 Δmean **0.015**
    （裁决前「内容之上」为 **2.11** / maxΔ 9.3）、浅底 Δmean **5.47**（⇒ 背景仍有光）；
    连跑 3 次逐位一致。⚠ `isolation:isolate` 不可省：否则 `z-index:-1` 会**逃到祖先背景之后**而不可见。
  - ★★ **三层独立阻断**（批十三源码级勘察）：`.hero__map` 一处就叠了三层 —— ① 原 `pointer-events: none`
    ⇒ 指针**根本命中不到**；② **SVG 元素不能承载 CSS 伪元素** ⇒ `svg::before` 结构上不存在，
    必须补 HTML wrapper；③ CSS/JS 的作用面 selector 写死 `.card`。
    ⇒ 纪律：报「某特效没生效」时**先列全部可能阻断层**（命中测试／宿主能力／作用面选择器／层叠与 z-index），
    逐层实测哪层先断，**修好一层必须重测**（后面的层可能仍在断）。
  - **定性**：本层是 `decor`（装饰性反射面）⇒ 见上文「对象必须分类」的 `decor` 条。
    ⛔ 两道熔断（`prefers-reduced-motion`（以 `:not([data-motion='on'])` 限定）与 `[data-motion='off']`）不动。
  - `.hero__map` 的 wrapper 由 `<svg>` 改为 HTML 元素后**参与命中测试** ⇒ 同批新增
    `scripts/probes/hero_hit_probe.py`（CI runtime 硬阻）实测「未抢走 Hero 内主 CTA 与 `#featured` 锚点」，
    ⛔ 不靠「预期安全」推断。
- **夜间星野特效（tsparticles，MIT）**：`preset-stars` + 本站覆盖项，**叠加**在银河照片之上。  懒加载（`next/dynamic({ssr:false})`）⇒ ⛔ 不进首屏 JS（实测 `/` 仍 106 kB，粒子独立分块 105 KB）。
  两条熔断**必须保留**：`prefers-reduced-motion: reduce` 与 `[data-motion='off']` 下**卸载画布**
  （浅色档同理：`display:none` 只是「不显示」，rAF 仍在算）。判据见
  `batch6-evidence/verify_backdrop_fx.py`（含「画布 backing = CSS × DPR」的清晰度机检）。
  ⚠ **批十一 · 真机归因分离已裁定（2026-10-09，部署 `a694887`）**：`be457d8` 曾**同时**上
  「关 `grab`」与「关 `detectRetina`」两项，无法归因 ⇒ 批十一把 `detectRetina` 改回 `true` 做**单因子 A/B**。
  用户（华为畅享70X / HarmonyOS 4.2.0 / 微信浏览器）实测「**不卡，有特效**」
  ⇒ **`grab` 是主因、retina 无关** ⇒ **保留 `true`**（拿回 2x/3x 屏锐利圆点），
  「星点变柔」这条代价**已撤销**。⚠ 若日后低端机再现掉帧，本条是**首选回归项**（须重走单因子 A/B）；
  ⛔ `onHover.enable` 那条**不改回**（正确性主张，非性能手段）。
  ★ 批八（裁决④ · T2）**只调「可发现性」这一维**（`grab.distance` 190→260、`links.opacity` 0.22→0.45），
  ⛔ 不加新交互模式、不加依赖、不新增字节。**星野仍是有意的夜间专属**：浅底上白星不可见，
  改成深色星点会引入一条没有任何裁决依据的新视觉母题 ⇒ 主题对称性由上面那道**主题无关的指针光斑**承担。
- **长页目录（`TocSidebar`）**：`≥1280px` 为**粘性侧栏**（右列）；**`<1280px` 单列时隐藏**（★ 批十一裁决）。
  原因：单列下 `.detail__aside` 按文档流排在正文**全部 section 之后**（实测 `/about@390`：目录 `top=3822`、
  `/stats@390`：`top=5085`）⇒ 页尾目录在移动端基本无用。隐藏是**如实登记「移动端无目录」**，
  ⛔ 不是「已适配」。⛔ 不要改成 `order:-1` 提到前面（目录块实测高 226–326px，
  会挡在**页面标题之前**）；⛔ 也不要另造第二份移动端目录（DOM 重复 ⇒ 重复 landmark 与锚点）。
- **网格/弹性子项必须显式收缩**：`grid-template-columns: 1fr` 与 flex 子项默认 `min-width: auto`
  ⇒ **不会收缩到内容最小宽度以下**。实测：`.detail__main` 漏了这一条，窄屏被构建期 ECharts SVG
  与指标表撑到 653px（视口 390）整页截断。宽内容请放进带 `overflow-x:auto` 的容器
  （`.chart__frame` / `.mtable__scroll`）并给外层 `min-width: 0`。
- **内联 SVG 图件**（`src/components/figures/*`）为**手工定位**（无布局引擎）⇒
  几何缺陷不会自己暴露。判据＝活件 `scripts/probes/svg_layout_probe.py`（**CI runtime 硬阻**；
  归档件 `batch6-evidence/verify_svg_layout.py`）：
  `S1` 文字压框/压字、`S2` 箭头落点（矩形切边合法／圆形须留 ≥4px 净距），带 `--selftest` 负向夹具。
  ⚠ **声明的不覆盖面**：`circle`/`ellipse`/`path` 不判（圆的外接正方形会把「环内中央的文字」
  误报为重叠）。改动图件后必须重跑该判据。

## 已知取舍

- ★ **术语解释层面板曾被 `.mtable__scroll`（`overflow-x:auto`）裁剪 —— 第十六批 W4/C3 已修**（缺陷系第十五批
  实测发现、`batch14 W2-2` 起即存在）：`.term__def` 原为 `position:absolute`，宿主在滚动容器内
  ⇒ 被容器 padding box 裁剪（**实测**：表头最右列面板越容器**右缘 213px**、末行越**下缘 179px**）。
  **修法**＝`MotionRuntime` 的委托（与既有 Esc/离开同处）在面板**已展开**时落 `data-term-float`
  ＋ 视口坐标，CSS 把面板切成 `position:fixed`（containing block ＝ **视口** ⇒ 逃裁剪；**实测亦逃层叠**：
  fixed 面板越容器下缘仍命中自身，absolute 则命中下一 `.mtable__block`）。
  ⚠ **展示仍全由 CSS 裁决**（`:hover` / `:focus-within` / `[data-term-closed]`），JS **只改定位**
  —— ⛔ 不开第二条互相打架的呈现路径（b95）。判据：`term_layer_probe.T7`（逐件命中测试 ＋ `--selftest` 负向夹具）。
  ⛔ 判据**不能**写成「面板 rect ⊆ 容器 rect」：已修形态的面板**本就**落在容器外，那种比较会把修好的判 FAIL。
  ⚠ **代价（如实登记）**：**无 JS 时仍是原来的 `position:absolute`** ⇒ 该路径在滚动容器内**仍会被裁**
  （定义文本照旧常驻 HTML、读屏与无 JS 取文本不受影响，仅视觉被裁）。⛔ 未采用 Popover API：
  其声明式只支持**点按**触发，会打断 hover/focus 路径且与既有 CSS 呈现路径打架；亦未用纯 CSS
  Anchor Positioning（需**每实例唯一 `anchor-name`**，而 `Term` 是 RSC 无 `useId`，且支持面 partial）。
- ⚠ **术语面板的 `id` 在同一页内重复**（第十六批 W4/C3 期间发现，⛔ **未修**）：`Term` 用
  `glossary-<词条 id>` 作面板 `id`，而同一词条在同页会多次出现（`/stats` 实测 **`glossary-missing` ×22 ·
  `glossary-collectability` ×10**，计数类词条各 ×4）⇒ 违反 HTML `id` 唯一性。
  功能上 `aria-describedby` 解析到**首个**同名面板（内容逐字相同 ⇒ 读屏不受实质影响）
  ⇒ 属**规范/有效性**缺陷，非功能性缺陷。⚠ **既有判据不覆盖**：`axe_a11y_probe` 用的 axe-core 4.14
  **已移除** `duplicate-id*` 规则族（故它不会报）。
  修法方向＝面板 `id` 每实例唯一；⚠ `Term` 是**服务端组件**（无 `useId`）⇒ 须由调用侧传唯一键，
  或把 `Term` 改为客户端组件（代价＝包体）。⛔ 未做，登记待裁决。
- ★ **hero 定位图「聚焦方向 → `/works` 筛选域」的映射是人工声明，且其中一条不等值**（十七批 W4-②，
  **用户裁决** 2026-10-11「三方向全按 domain 映射」）：`机器学习建模 → domain=llm`（域名标签是「大模型」，
  与源标签**不同字**）⇒ 是全表**最弱的一环**；另两条字面/语义可辩护
  （`AI Agent 工程→agent-engineering`、`运筹优化→algorithms`）。⚠ 两条**实测否定**：
  `q=机器学习` / `q=建模` / `q=优化` / `q=运筹` 在目录里命中 **0** ⇒ 文本搜索接不上，只能走 domain。
  ★ 缓解：链接 `aria-label` 与目标页的筛选 chip 都会**显形实际生效的域名** ⇒ 所见符合所得。
  ⛔ 词表与目标域不适配属**口径问题**（不是数据问题）⇒ 由用户裁决，⛔ 执行方不擅扩表。
- 静态导出 + 客户端筛选 ⇒ 首屏共享 JS 约 102 KB（React 运行时基线）。相比 v1 的 Astro（零 JS 基线）
  是本次换栈明确接受的成本；换来的是完整 React 生态的交互上限。
- **CI 时长**：把浏览器层判据升为 runtime 硬阻后，构建作业多出「装 playwright ＋ chromium ＋
  起静态服务 ＋ 跑浏览器层探针」一段（浏览器二进制有缓存但仍需 apt 依赖）。这是**有意接受**的成本 ——
  换来的是「提示词级（可绕）」→「runtime 硬阻（结构上做不成）」（落地形态强度阶梯）。
- **W1 的 `decor` 定性是「治理选择」而非「技术必然」**（第十三批，2026-10-10 用户裁决）：
  「所有带框容器统一加指针高光」（V1）与本站「悬停反馈面 ≡ 点击热区」判据**互锁**，
  解法的代价是**判据面变化** —— 多了一个 `kind: decor`，并让 `surface_hit_probe` /
  `gate_interaction_surface` 各带 `decor` 分支。两边**同批改**且都有 `--selftest` 负向夹具
  （含「decor 面内含交互目标必须回退判覆盖率」，⛔ 防它成为逃生门）。
- **高光层的层叠位置＝内容之下**（批十四 W1c 落地用户裁决 V7，2026-10-10）：
  `[data-spotlight]{isolation:isolate}` ＋ `[data-spotlight]::before{z-index:-1}` ⇒ `::before` 排在
  「宿主背景之上、静态内容之下」，悬停时文字/SVG **不再**被镀 tint。
  ★ 像素实测（图注文字条的不透明字形核心像素）：字形 Δmean **0.015**（裁决前「内容之上」为 **2.11** / maxΔ 9.3）；
  浅底 Δmean **5.47** ⇒ 背景仍有光。连跑 3 次逐位一致（量测稳定性判据，见 §7 b136）。
  ⚠ `.card` 自第八批起原是「内容之上」；本次**统一为「内容之下」**，属**用户裁决的观感变更**（V7）。
  对比预览件 `batch13-evidence/decor-preview.html`（A＝旧「内容之上」 / B＝新「内容之下」，内置
  **动效三态开关 ＋ 熔断诊断行** —— ⚠ 高光受两道熔断压制，OS 开「减少动画」时须先切「动效开」）
  ＋ `batch13-evidence/preview-shots/`。
- ⚠ **`[data-spotlight]` 已按 §4-W1 表全量接入**（`.card` / `.figure` / `.chart__frame` / `.threads` /
  `.hero__map` / `.metrics__item` / `.related__item` / `.directory__item` / `.contact__link` /
  `.disclosure` / `li.chip` / `span.chip` / `.hero__eyebrow`），排除项见上文「排除项（三条）」
  （★ 十七批把 `.hero__map` 移出该清单 ⇒ 该清单已由 9 项变 8 项）。
  ⛔ 但**「接入」≠「观感已裁决」** —— 高光强度是否合适仍未人看对比件（见下一条）。
- ★ **修掉一处**新暴露的**既有**缺陷（批十三收口，非本功能引入）：echarts 构建期 SSR 会为系列生成
  `.zr0-cls-N:hover { cursor:pointer; fill:… }`，而本站是**纯静态导出、这些条没有任何动作**
  ⇒ 悬停 `cursor:pointer` ＋ 变色＝**假可供性**（本站自有判据明确禁止）。
  修法＝`scripts/build_charts.mjs` 里 `stripHoverRules()` **删掉 SSR 输出的 `:hover` 规则**
  （结构上让它不存在）。⛔ 不登记 `.zr0-cls-N`：其取值由 echarts 内部决定 ＝ 会腐化的字面常量。
  悬停反馈改由 `.chart__frame`（`decor` 高光）承担 —— 反馈落在**框**上而非数据条上，一致性更好。
   ⚠ 该缺陷此前被「`surface_hit_probe` 的 `RUNS` 不含 `/stats/`」**静默掩盖**；本批把该路由纳入
   同类项全集后才暴露（⇒ 新增作用面必须同步纳管其所在路由）。
- ★ **十七批 W4-③：图表 ↔ 表格 联动高亮**（`/stats`）。悬停图表某条 ⇒ 高亮**对应项目**的整组表行；
  悬停表行 ⇒ 反向高亮该条。三条要点：
  ① **按「项目身份」配对，⛔ 不按下标**：两端都带 `data-project`。⭐ 这是一条**实测更正** ——
     图表 SSR 的 `<path>` **自带 `ecmeta_data_index`**（echarts 元数据），早前「产物无任何标识」的印象
     源自 grep 把前缀写成了 `data-`（真实是 `ecmeta_`）⇒ **无需改生成器**；
     且图按**值升序**、表按**目录序**（实测图首项 `dsh-manager-analysis` ≠ 表首项 `12-factor-methodology-kg`）
     ⇒ 按下标会**静默错配**。
  ② **注解只在渲染期**（`lib/metrics.ts` 的 `annotateChartBars`）：`charts.json` 一字不改，
     ⛔ 站点侧语义不进数据产物。
  ③ **作用面只限「有图的项目」**（10 项里 7 项）：文档集群区/论文库区/未分区没有图，⛔ 不给它们打
     `data-project` —— 否则会出现「悬停表格行却什么也不发生」＝ 看起来有联动其实没有（违反轴 B）。
  ⚠ **与上一条的关系**：本联动**不**给数据条加 `:hover`、不改 `cursor`（批十三已删掉 SSR 的
  `cursor:pointer`）⇒ 不重开「假可供性」；高亮是**联动态**（CSS 属性选择器 `[data-hl]`，JS 只落属性）。

## 留档

架构决策（ADR-001）与选型矩阵见 Mission 目录 `1008-个人主页深化改革/`。
