const CX = 210;
const CY = 152;
const R = 96;
const NODE_R = 36;

/** 顺时针：上 → 右 → 下 → 左。步骤名取自 `PROFILE_PRACTICE` 的四条原则，压缩成 2–3 字。 */
const STEPS = [
  { angle: -90, index: '01', label: '定口径' },
  { angle: 0, index: '02', label: '再采数' },
  { angle: 90, index: '03', label: '验产物' },
  { angle: 180, index: '04', label: '做复盘' },
];

function point(angleDeg: number, radius: number): { x: number; y: number } {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: CX + radius * Math.cos(rad), y: CY + radius * Math.sin(rad) };
}

/**
 * 「工作方式」闭环图（第五批新增）。
 *
 * ★ 为什么出这张图：原先 `/about` 的工作方式是四条并列的项目符号 ——
 *   但它们的真实关系是**闭环**（口径错了要回炉、复盘产出下一轮口径），
 *   并列列表把「环」表达成了「清单」，信息被抹平。图的形状本身就是论据。
 * ★ 环上的四个节点只写**动作**；每条动作的展开说明仍在下方文本清单里
 *   （图给结构、文给细节，⛔ 不做成两处各说一遍）。
 */
export function PracticeCycleFigure() {
  return (
    <svg className="figure__svg" viewBox="0 0 420 304" role="img" aria-labelledby="practice-fig-title">
      <title id="practice-fig-title">
        工作方式闭环图：先定口径，再采数，然后验证产物，最后复盘；复盘的结果回流成为下一轮的口径修正。
      </title>

      <defs>
        <marker
          id="practice-arrow"
          viewBox="0 0 8 8"
          refX="7"
          refY="4"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M0 0.6 L7.4 4 L0 7.4 z" className="dg-accent" />
        </marker>
      </defs>

      <circle className="dg-orbit" cx={CX} cy={CY} r={R} />

      {STEPS.map((step, i) => {
        const next = STEPS[(i + 1) % STEPS.length];
        // ★ 弧线端点的角度留白：要让**箭头标记整体留在节点圆外**。
        //   标记长度 = markerWidth(7) × strokeWidth ⇒ 端点仅贴在圆周上时箭头会压住圆（实测）。
        //   取圆心到端点弦长 ≥ NODE_R + 9px ⇒ 2R·sin(gap/2) ≥ 45 ⇒ gap ≥ 27°。
        const gap = 27;
        const start = point(step.angle + gap, R);
        const end = point(next.angle - gap, R);
        return (
          <path
            className="dg-edge"
            d={`M ${start.x} ${start.y} A ${R} ${R} 0 0 1 ${end.x} ${end.y}`}
            markerEnd="url(#practice-arrow)"
            key={`arc-${step.index}`}
          />
        );
      })}

      {STEPS.map((step) => {
        const p = point(step.angle, R);
        return (
          <g key={step.index}>
            <circle className="dg-node dg-node--brand" cx={p.x} cy={p.y} r={NODE_R} />
            <text className="dg-step" x={p.x} y={p.y - 3} textAnchor="middle">
              {step.index}
            </text>
            <text className="dg-label" x={p.x} y={p.y + 13} textAnchor="middle">
              {step.label}
            </text>
          </g>
        );
      })}

      <text className="dg-center" x={CX} y={CY - 2} textAnchor="middle">
        同一套口径
      </text>
      <text className="dg-center dg-center--sub" x={CX} y={CY + 15} textAnchor="middle">
        贯穿四步
      </text>
    </svg>
  );
}
