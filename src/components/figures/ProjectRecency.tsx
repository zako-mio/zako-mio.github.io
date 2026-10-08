import { recencyRatioOf, shortDate, type RecencyRange } from '@/lib/recency';
import type { Project } from '@/lib/schema';

export interface ProjectRecencyProps {
  project: Project;
  /** 由服务端页面算好并逐层传下来的**共享**标尺；为 null 时本件不渲染。 */
  range: RecencyRange | null;
}

/**
 * 卡片上的「新鲜度标尺」（第五批新增）。
 *
 * ★ 它回答的是**卡片上原本没有的信息**：这个项目在全部项目的活跃时间轴上落在哪。
 *   ⇒ 不是把下方已有的文字换个画法，而是补上「相对位置」这一维。
 * ★ 全部卡片共用同一段 [最早, 最新]，因此卡片之间的点**可以直接横比**。
 * ★ 无数据即**不画**（⛔ 不拿 0 或中点冒充位置）。
 * ★ 纯呈现、无取数 ⇒ 可安全地被客户端组件（`WorksExplorer`）间接引用；
 *   服务端渲染的内联 SVG ⇒ 无 JS 可读、无额外请求，语义经 `role`/`aria-label` 暴露。
 */
export function ProjectRecency({ project, range }: ProjectRecencyProps) {
  const ratio = recencyRatioOf(project.pushed_at, range);
  if (ratio === null || range === null) return null;

  const width = 240;
  const left = 8;
  const right = width - 8;
  const x = left + ratio * (right - left);
  const label = project.pushed_at ? project.pushed_at.slice(0, 10) : '未记录';
  const percent = Math.round(ratio * 100);

  return (
    <svg
      className="card__figure"
      viewBox={`0 0 ${width} 34`}
      role="img"
      aria-label={`活跃度标尺：本项目最后提交于 ${label}，在全部项目时间轴上的相对位置为 ${percent}%`}
    >
      <title>{`活跃度标尺：最后提交 ${label} · 相对位置 ${percent}%`}</title>

      <text className="fp-cap" x={left} y="8">
        {shortDate(range.min)}
      </text>
      <text className="fp-cap fp-cap--end" x={right} y="8">
        {shortDate(range.max)}
      </text>

      <line className="fp-track" x1={left} y1="21" x2={right} y2="21" />
      <line className="fp-fill" x1={left} y1="21" x2={x} y2="21" />
      <line className="fp-tick" x1={left} y1="17" x2={left} y2="25" />
      <line className="fp-tick" x1={right} y1="17" x2={right} y2="25" />

      <circle className="fp-halo" cx={x} cy="21" r="6" />
      <circle className="fp-dot" cx={x} cy="21" r="3.4" />
    </svg>
  );
}
