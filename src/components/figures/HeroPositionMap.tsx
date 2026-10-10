import { PROFILE_FOCUS, PROFILE_FOCUS_FILTERS } from '@/lib/profile';
import { DOMAIN_LABELS } from '@/lib/schema';

/**
 * 首屏右区「定位图」（第八批 · 裁决② 选定的 V3 方案；第十七批 W4-② 加节点交互）。
 *
 * ★ 从**装饰**升级为**信息件**（第八批裁决要点）：旧件 `HeroFigure` 是 `aria-hidden` 的纯装饰星座
 *   （不承载信息；夜间该区高亮像素占比 0.000）。本件把 Hero 那句话的**结构**画出来 ——
 *   「复合背景 → 核心动作 → 三个聚焦方向」，让首屏最大的视觉权重（右侧 35% 空间）承载
 *   与首页职能自洽的内容。
 *
 * ★ IA 纪律（有意的自我约束）：本件只**重述 Hero 已有的定位陈述**（同一页内的一次图形化再表达）：
 *   ⛔ 不引入 `/stats` 的聚合数字、⛔ 不引入 `/works` 的作品枚举、
 *   ⛔ 不与 `/about` 的画像分组（背景/技术方向/兴趣）重复成第二处正文。
 *   标签只取自定位陈述里的「复合背景」两线与 `PROFILE_FOCUS` 的三个方向。
 *
 * ★ `<1024px` 隐藏（沿用本站既有的右区口径）：那份信息**在同页正文里以文字存在**（Hero 标语）
 *   ⇒ 隐藏它不造成信息丢失（这正是「图形化」而非「新信息」的必然结果）。
 * ★ 标签用**带底色的 chip**：① 可读性（不受背景细节影响）；② 连接线画在 chip **下层**，
 *   不会穿字（判据侧见 `batch6-evidence/verify_svg_layout.py` 的 S1）。
 *
 * ★ 第十三批（W1）：外包一层 HTML wrapper 承接指针高光。缘由是**三层独立阻断**（坑手册 b119/b120）：
 *   ① SVG 元素**不能承载 CSS 伪元素** ⇒ `svg::before` 结构上不可能存在，必须另找宿主；
 *   ② 原 `.hero__map` 带 `pointer-events: none` ⇒ 指针**根本命中不到**（`closest()` 永远返回 null）；
 *   ③ 伪元素宿主必须是**已定位**（`position != static`）的 HTML 元素，`.hero__map` 的绝对定位
 *      随之移到 wrapper 上（⛔ wrapper 的居中仍用独立的 `translate` 属性，见下方 CSS 注释）。
 *
 * ★ 第十七批（W4-②，用户 2026-10-11 裁决「全 B」）：**三个聚焦方向变成真链接**，
 *   激活后到 `/works` 按对应方向（domain）筛选。三条设计约束（每条都有实测理由）：
 *   ① **`<a>` 只包 chip，⛔ 不包连接线**：`hero_hit_probe` 的 H1 判「可交互件的**几何中心**
 *      必须命中回它自己或其后代」，而 `union(线, chip)` 的包围盒中心落在**空隙**里
 *      ⇒ 包线会直接触发 H1 假 FAIL（本批实测过该几何）。
 *   ② **连接线的高亮由 `MotionRuntime` 委托 ＋ `data-hl` 承担**（⛔ 不用 CSS `:hover` 规则）：
 *      线与节点分属两个 `<g>`，要用 CSS 关联就得**逐条写 N 条规则**，而那些规则的选择器会落进
 *      `interaction-surfaces.json` 的登记集合、并按**容器口径**判覆盖率（细斜线命中率必为 0）
 *      ⇒ 假 FAIL。改走「JS 落属性、CSS 属性选择器上色」，与既有的 `--mx/--my`、「`data-pointer`」
 *      模式同构（JS 只写状态，呈现仍由 CSS 裁决）。
 *   ③ **`<a>` 必须显式 `pointer-events: auto`**：`.hero__map__svg` 是 `pointer-events: none`
 *      （W1 的不抢命中约定）⇒ 不在链接上重新启用就是**结构性哑火**（点不动，且 H1/H4 都会抓到）。
 *
 * ★ 可访问性口径（本批**有意变更**，⛔ 不是顺手改）：
 *   第八批把本图定为 `role="img"` ＋ title/desc「给等价文本」——那在**纯装饰/纯信息**时是对的；
 *   但 `role="img"` 会把子树**压平**（子节点不进可访问性树）⇒ 与「方向可点」**结构上不相容**。
 *   ⇒ 改为 `role="group"`（带名）＋ 内部文本自然可读 ＋ `<desc>` 只讲**怎么读/能做什么**
 *     （⛔ 不再复述节点文字，避免同一信息两遍 —— 与「两处⛔ 不各说一遍细节」同源）。
 *   ⚠ 三个方向链接各自带 `aria-label`（含**实际生效的筛选域名**），保证「所见符合所得」对读屏同样成立。
 */
const LEFT = ['电商管理', '数据科学'];

/** 三个方向 chip 的几何与它那条连接线：y 与连线端点沿用既有坐标，⛔ 本批不动布局。 */
const FOCUS_ROWS = [
  { rectY: 69, edgeKey: 'f0', edgeD: 'M260 166 L288 84' },
  { rectY: 165, edgeKey: 'f1', edgeD: 'M260 180 L288 180' },
  { rectY: 261, edgeKey: 'f2', edgeD: 'M260 194 L288 276' },
];

export function HeroPositionMap() {
  const focus = PROFILE_FOCUS.slice(0, 3).map((label, index) => ({
    label,
    domain: PROFILE_FOCUS_FILTERS[label],
    ...FOCUS_ROWS[index],
  }));

  // ★ 批十七 W4-②：**去掉了 wrapper 上的 `data-spotlight="soft"`**（批十三 W1 为它专门加的整图指针高光）。
  //   理由不是观感偏好，而是**判据判出来的真缺陷**：该高光的反馈面＝**整块图**（boxArea 151200），
  //   而本批之后图内只有 3 个 chip 是热区 ⇒ `surface_hit_probe` 按 `container` 口径量得
  //   coverage **0.074**（hot 9 / considered 121）< 0.98 ⇒ FAIL（「错位（含死区）」）。
  //   这正是用户轴 B 的机检形态：**反馈面 > 热区 ＝ 假可供性**（看起来整块能点，实际只有三处能点）。
  //   ⇒ 二选一：① 去掉整图高光（本批采纳）；② 让整块图可点（语义上做不到）。
  //   ⚠ 代价如实登记：图件不再有指针跟随高光（W1 的那一项对它失效）；chip 自身仍有 hover/focus 反馈。
  //   ⛔ 若将来要恢复整图高光，必须同时把「整块图」变成真交互面（否则判据必再 FAIL）。
  return (
    <div className="hero__map">
      <svg
        className="hero__map__svg"
        viewBox="0 0 420 360"
        role="group"
        aria-labelledby="hero-map-title"
        aria-describedby="hero-map-desc"
        focusable="false"
      >
        <title id="hero-map-title">定位图</title>
        <desc id="hero-map-desc">
          由「{LEFT.join(' × ')}」复合背景汇聚，落到核心动作「端到端决策落地」，再展开为三个聚焦方向。
          三个方向各是一个链接，激活后到作品页按对应方向筛选；其余标签只作定位说明，不可点。
        </desc>

        {/* 连接线在下层：chip 有实底 ⇒ 不会出现线穿字 */}
        <g className="hm-edge">
          <path d="M114 140 L140 166" />
          <path d="M114 220 L140 194" />
          {focus.map((item) => (
            <path data-edge={item.edgeKey} d={item.edgeD} key={item.edgeKey} />
          ))}
        </g>

        {/* 背景两线（不可点：它们不指向任何作品筛选域） */}
        <g className="hm-chip">
          <rect x="4" y="125" width="110" height="30" rx="9" />
          <text x="59" y="140">
            {LEFT[0]}
          </text>
          <rect x="4" y="205" width="110" height="30" rx="9" />
          <text x="59" y="220">
            {LEFT[1]}
          </text>
        </g>

        {/* 核心动作（不可点） */}
        <g className="hm-chip hm-chip--core">
          <rect x="140" y="157" width="120" height="46" rx="11" />
          <text x="200" y="180">
            端到端决策落地
          </text>
        </g>

        {/* 三个聚焦方向：真链接（`<a>` 只包 chip —— 见头注①） */}
        {focus.map((item) => (
          <a
            className="hm-node"
            data-edge={item.edgeKey}
            href={`/works?domain=${item.domain}`}
            aria-label={`${item.label}：到作品页按「${DOMAIN_LABELS[item.domain]}」筛选`}
            key={item.label}
          >
            <g className="hm-chip">
              <rect x="288" y={item.rectY} width="126" height="30" rx="9" />
              <text x="351" y={item.rectY + 15}>
                {item.label}
              </text>
            </g>
          </a>
        ))}
      </svg>
    </div>
  );
}
