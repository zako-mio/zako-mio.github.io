export interface BrandMarkProps {
  size?: number;
  className?: string;
}

/**
 * 站点标记（第五批新增）。
 *
 * ★ 图形化表达的一处落地：⛔ 不是装饰性贴图，而是**用图形说出站点在讲什么**——
 *   三个节点 + 有向边 = 「知识图谱 / DAG 组织」，外圈弧 = 「工具链环绕」，
 *   中心实心点 = 「以结论为中心」。它同时充当 favicon 与左栏 masthead 的标记。
 * ★ 纯内联 SVG、构建期渲染 ⇒ 无请求、无 JS、可被屏幕阅读器经 <title> 取到语义。
 */
export function BrandMark({ size = 38, className }: BrandMarkProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role="img"
      aria-label="zako-mio 站点标记：三节点有向图"
    >
      <title>三节点有向图：以结论为中心的知识组织</title>
      <defs>
        <linearGradient id="bm-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" style={{ stopColor: 'var(--brand-bright)' }} />
          <stop offset="100%" style={{ stopColor: 'var(--brand-deep)' }} />
        </linearGradient>
      </defs>

      <rect x="0" y="0" width="48" height="48" rx="13" fill="url(#bm-fill)" />

      <g
        fill="none"
        stroke="rgba(255,255,255,0.92)"
        strokeWidth="1.6"
        strokeLinecap="round"
      >
        <path d="M13 33 L24 13" />
        <path d="M24 13 L35 31" />
        <path d="M13 33 L35 31" strokeDasharray="3 3" strokeOpacity="0.7" />
      </g>

      <circle cx="24" cy="13" r="3.1" fill="#ffffff" />
      <circle cx="13" cy="33" r="2.6" fill="#ffffff" fillOpacity="0.85" />
      <circle cx="35" cy="31" r="2.6" fill="#ffffff" fillOpacity="0.85" />

      <circle
        cx="24"
        cy="24"
        r="18"
        fill="none"
        stroke="rgba(255,255,255,0.32)"
        strokeWidth="1"
        strokeDasharray="2 6"
        strokeLinecap="round"
      />
    </svg>
  );
}
