interface Node {
  col: number;
  y: number;
  title: string;
  sub: string;
}

/**
 * 「本站是怎么做的」结构图（第五批新增）。
 *
 * ★ 为什么出这张图：本站的做法本来是用三段文字说的（见 `SiteBuildNotes`）。
 *   但「源 → 管道 → 产物 → 呈现」本质是一条**有向链**，
 *   链式结构的正确表达是图，不是分段文字 —— 这正是本轮的可读性主张。
 * ★ 图上**不写任何数字**（⛔ 计数唯一落点是 `/stats`），只写角色与流向。
 * ★ 服务端渲染内联 SVG：无 JS 可读、无请求；整图靠 `<title>` 提供等价文本。
 */
const W = 168;
const H = 48;
const COLS = [24, 232, 440, 648];
// 图高：第 4 列末节点 226+48=274 ⇒ 留出 6px 余量（原 268 会切掉底部）
const VIEW_H = 280;
const HEADS = ['源', '管道', '产物', '呈现'];

const NODES: Node[] = [
  { col: 0, y: 126, title: '公开项目仓库', sub: '每日回源，不手抄' },

  { col: 1, y: 40, title: '采集', sub: 'sources → domain' },
  { col: 1, y: 126, title: '口径规范', sub: '先定口径再采数' },
  { col: 1, y: 212, title: '门控', sub: '读真实产物 + 负向夹具' },

  { col: 2, y: 40, title: 'projects.json', sub: '过契约校验的索引' },
  { col: 2, y: 126, title: 'metrics.json', sub: 'E 指标 + 人工确认登记' },
  { col: 2, y: 212, title: 'charts / topology', sub: '构建期 SVG 与分层复算' },

  // ★ 第 4 列首节点原为 y=8，而列头「呈现」画在 y=16 ⇒ 列头压在节点框上（实测交叠 0.9）。
  //   列头必须**独占一行**：整列下移并在 viewBox 底部让出空间（见 VIEW_H）。
  { col: 3, y: 34, title: '首页', sub: '定位与枢纽' },
  { col: 3, y: 98, title: '作品', sub: '全量索引与筛选' },
  { col: 3, y: 162, title: '聚合', sub: '数字与口径边界' },
  { col: 3, y: 226, title: '关于', sub: '画像与联系' },
];

const EDGES: Array<[number, number]> = [
  [0, 1],
  [0, 2],
  [0, 3],
  [1, 4],
  [1, 5],
  [2, 5],
  [3, 6],
  [4, 7],
  [4, 8],
  [5, 9],
  [6, 9],
];

function edgePath(from: Node, to: Node): string {
  const x1 = COLS[from.col] + W;
  const y1 = from.y + H / 2;
  const x2 = COLS[to.col];
  const y2 = to.y + H / 2;
  // 水平控制点的三次贝塞尔：等宽列之间形成统一的「汇流 / 扇出」节奏
  const control = Math.max(18, (x2 - x1) * 0.45);
  return `M ${x1} ${y1} C ${x1 + control} ${y1}, ${x2 - control} ${y2}, ${x2} ${y2}`;
}

export function StructureFigure() {
  return (
    <svg
      className="figure__svg"
      viewBox={`0 0 840 ${VIEW_H}`}
      role="img"
      aria-labelledby="struct-fig-title"
    >
      <title id="struct-fig-title">
        本站做法结构图：公开项目仓库经采集、口径规范与门控三条管道，产出索引、指标与图表三类产物，
        再分发到首页、作品、聚合、关于四个呈现面。
      </title>

      <defs>
        <marker id="struct-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0.6 L7.4 4 L0 7.4 z" className="dg-accent" />
        </marker>
      </defs>

      {HEADS.map((head, index) => (
        <text className="dg-head" x={COLS[index]} y="16" key={head}>
          {head}
        </text>
      ))}

      <g>
        {EDGES.map(([from, to]) => (
          <path
            className="dg-edge"
            d={edgePath(NODES[from], NODES[to])}
            markerEnd="url(#struct-arrow)"
            key={`${from}-${to}`}
          />
        ))}
      </g>

      {NODES.map((node) => (
        <g key={`${node.col}-${node.y}`}>
          <rect
            className={node.col === 3 ? 'dg-node dg-node--brand' : 'dg-node'}
            x={COLS[node.col]}
            y={node.y}
            width={W}
            height={H}
            rx="11"
          />
          <text className="dg-label" x={COLS[node.col] + 14} y={node.y + 20}>
            {node.title}
          </text>
          <text className="dg-sub" x={COLS[node.col] + 14} y={node.y + 36}>
            {node.sub}
          </text>
        </g>
      ))}
    </svg>
  );
}
