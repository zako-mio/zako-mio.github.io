/**
 * Hero 图形副件（第五批新增，纯装饰）。
 *
 * ★ 与 `BrandMark` 同源语汇（节点 + 有向边 + 虚线圈），把它放大成一张「星座」：
 *   左侧的三节点小图 → 汇聚到中心 → 右侧展开成扇出。
 *   读者不必读文字也能看出「输入收敛 → 加工 → 产出」这件事。
 * ★ `aria-hidden` —— 纯装饰，不承载信息，⛔ 不让读屏器读一串无意义的点。
 * ★ 颜色全部走令牌（`currentColor` / CSS 变量）⇒ 换主题时图随主题走。
 */
export function HeroFigure() {
  return (
    <svg className="hero__figure" viewBox="0 0 360 360" aria-hidden="true" focusable="false">
      <g className="hf-edge">
        <path d="M46 96 L150 176" />
        <path d="M46 180 L150 180" />
        <path d="M46 264 L150 184" />
        <path d="M186 180 L292 84" />
        <path d="M186 180 L292 180" />
        <path d="M186 180 L292 276" />
      </g>

      <g className="hf-orbit">
        <circle cx="168" cy="180" r="118" />
        <circle cx="168" cy="180" r="86" />
      </g>

      <g className="hf-node">
        <circle cx="46" cy="96" r="7" />
        <circle cx="46" cy="180" r="7" />
        <circle cx="46" cy="264" r="7" />
        <circle cx="292" cy="84" r="7" />
        <circle cx="292" cy="180" r="7" />
        <circle cx="292" cy="276" r="7" />
      </g>

      <circle className="hf-core" cx="168" cy="180" r="17" />
      <circle className="hf-core-inner" cx="168" cy="180" r="6" />
    </svg>
  );
}
