import { PROFILE_FOCUS } from '@/lib/profile';

/**
 * 首屏右区「定位图」（第八批 · 裁决② 选定的 V3 方案）。
 *
 * ★ 从**装饰**升级为**信息件**（本批裁决要点）：旧件 `HeroFigure` 是 `aria-hidden` 的纯装饰星座
 *   （不承载信息；夜间该区高亮像素占比 0.000）。本件把 Hero 那句话的**结构**画出来 ——
 *   「复合背景 → 核心动作 → 三个聚焦方向」，让首屏最大的视觉权重（右侧 35% 空间）承载
 *   与首页职能自洽的内容。
 *
 * ★ IA 纪律（有意的自我约束）：本件只**重述 Hero 已有的定位陈述**（同一页内的一次图形化再表达）：
 *   ⛔ 不引入 `/stats` 的聚合数字、⛔ 不引入 `/works` 的作品枚举、
 *   ⛔ 不与 `/about` 的画像分组（背景/技术方向/兴趣）重复成第二处正文。
 *   标签只取自定位陈述里的「复合背景」两线与 `PROFILE_FOCUS` 的三个方向。
 *
 * ★ 可访问性（裁决明列）：**撤掉 `aria-hidden`**，改 `role="img"` ＋ `<title>`/`<desc>`
 *   给等价文本 —— ⛔ 不得对承载信息的可见内容用 `aria-hidden`。
 * ★ `<1024px` 隐藏（沿用本站既有的右区口径）：那份信息**在同页正文里以文字存在**（Hero 标语）
 *   ⇒ 隐藏它不造成信息丢失（这正是「图形化」而非「新信息」的必然结果）。
 * ★ 标签用**带底色的 chip**：① 可读性（不受背景细节影响）；② 连接线画在 chip **下层**，
 *   不会穿字（判据侧见 `batch6-evidence/verify_svg_layout.py` 的 S1）。
 */
const LEFT = ['电商管理', '数据科学'];

export function HeroPositionMap() {
  return (
    <svg
      className="hero__map"
      viewBox="0 0 420 360"
      role="img"
      aria-labelledby="hero-map-title"
      aria-describedby="hero-map-desc"
      focusable="false"
    >
      <title id="hero-map-title">定位图</title>
      <desc id="hero-map-desc">
        由「{LEFT.join(' × ')}」复合背景汇聚，落到核心动作「端到端决策落地」，
        再展开为三个聚焦方向：{PROFILE_FOCUS.slice(0, 3).join('、')}。
      </desc>

      {/* 连接线在下层：chip 有实底 ⇒ 不会出现线穿字 */}
      <g className="hm-edge">
        <path d="M114 140 L140 166" />
        <path d="M114 220 L140 194" />
        <path d="M260 166 L288 84" />
        <path d="M260 180 L288 180" />
        <path d="M260 194 L288 276" />
      </g>

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

      <g className="hm-chip hm-chip--core">
        <rect x="140" y="157" width="120" height="46" rx="11" />
        <text x="200" y="180">
          端到端决策落地
        </text>
      </g>

      <g className="hm-chip">
        <rect x="288" y="69" width="126" height="30" rx="9" />
        <text x="351" y="84">
          {PROFILE_FOCUS[0]}
        </text>
        <rect x="288" y="165" width="126" height="30" rx="9" />
        <text x="351" y="180">
          {PROFILE_FOCUS[1]}
        </text>
        <rect x="288" y="261" width="126" height="30" rx="9" />
        <text x="351" y="276">
          {PROFILE_FOCUS[2]}
        </text>
      </g>
    </svg>
  );
}
