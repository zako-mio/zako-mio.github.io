import Link from 'next/link';

import { Term } from '@/components/Term';
import {
  METRIC_COLUMNS,
  SECTION_LABELS,
  loadMetrics,
  loadTopology,
  type GraphAnalysis,
  type MetricEntry,
} from '@/lib/metrics';

/**
 * 详情页「该项目图谱」区块（2b-5 / 2b-6）。
 *
 * 两层内容：
 *   1. 规模指标（metrics.json）：按 scope 分行，缺失渲染 `—`
 *   2. 结构实测（topology.json）：构建期 headless 拓扑计算的结果，
 *      **与项目自称并陈**；不一致处如实标注（E6：漂移本身是可信度信号）
 *   3. 数据出处（E4）：页面 URL ＋ 抓取时点 ＋ 文本指纹 ＋ 取值来源
 *
 * ★ 无 JS 可读：全部内容为服务端渲染的静态文字/表格，⛔ 不依赖任何画布。
 * ★ 能力层分工：cytoscape 在此只作**构建期拓扑内核**，画布交互留给项目站自身
 *   （记录 reject_when：「需要开箱即用的交互画布 ⇒ 应取 vis-network」）。
 */

function num(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : value.toLocaleString('en-US');
}

function ScopeTable({ entry, instanceKey }: { entry: MetricEntry; instanceKey: string }) {
  // ★ 必须套 `.mtable__scroll`（`overflow-x:auto`）：指标表列多、窄屏必然宽于视口，
  //   没有滚动容器时会把**整页**撑宽（实测 390px 下 403 vs 390，右侧被截断）。
  //   ⚠ 该 CSS 类此前只被 /stats 用上，本处漏了 —— 属「样式写了但标记没用」的死规则盲区。
  // ★ 批十八 V12：`instanceKey` 透传到列术语（`Term`）—— 保证同页面板 `id` 唯一。
  //   本页当前只渲染一张这样的表（列名本已唯一），透传是**面向将来**的显式声明：
  //   若日后同页出现第二张，⛔ 不必再回头找漏传点（由 `term_layer_probe.T8` 兜底）。
  return (
    <div className="mtable__scroll">
      <table className="mtable">
        <caption className="sr-only">该项目的规模指标（按 scope）</caption>
        <thead>
          <tr>
            <th scope="col">scope（图/视图）</th>
            {METRIC_COLUMNS.map((column) => (
              <th className="mtable__num" key={column.key} scope="col">
                <Term id={column.key} instanceKey={instanceKey}>
                  {column.label}
                </Term>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {entry.figures.map((figure) => (
            <tr key={figure.scope}>
              <td className="mtable__scope">{figure.scope}</td>
              {METRIC_COLUMNS.map((column) => (
                <td className="mtable__num" key={column.key}>
                  {num(figure[column.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GraphFacts({ graph }: { graph: GraphAnalysis }) {
  const { analysis, claimed, agreement } = graph;
  const mismatched = agreement?.acyclic === false || agreement?.layers === false;
  return (
    <li className="topo__item">
      <p className="topo__scope">
        <strong>{graph.scope}</strong>
        <span className="topo__asset">
          <a href={graph.url} rel="noreferrer noopener" target="_blank">
            {graph.asset}
          </a>
        </span>
      </p>
      <ul className="topo__facts">
        <li>
          节点 <strong>{num(analysis.node_count)}</strong> · 边 <strong>{num(analysis.edge_count)}</strong> ·
          连通分量 <strong>{num(analysis.component_count)}</strong>
        </li>
        <li>
          最长路径分层：
          {analysis.longest_path_layers === null ? (
            <>
              <strong>不可判定</strong>
              {analysis.cycle_sample && analysis.cycle_sample.length > 0 ? (
                <>
                  （存在有向环，例：<code>{analysis.cycle_sample.slice(0, 2).join(' ⇄ ')}</code>）
                </>
              ) : null}
            </>
          ) : (
            <strong>{analysis.longest_path_layers} 层</strong>
          )}
          {analysis.layer_note ? <span className="topo__note">· {analysis.layer_note}</span> : null}
        </li>
        {analysis.top_degree.length > 0 ? (
          <li>
            枢纽节点（度数）：
            {analysis.top_degree
              .slice(0, 3)
              .map((item) => `${item.id} ${item.degree}`)
              .join(' · ')}
          </li>
        ) : null}
        {analysis.top_betweenness && analysis.top_betweenness.length > 0 ? (
          <li>
            关键节点（介数中心性）：
            {analysis.top_betweenness.map((item) => `${item.id} ${item.score}`).join(' · ')}
          </li>
        ) : null}
        {claimed.acyclic !== null || claimed.layer_count !== null ? (
          <li className={mismatched ? 'topo__claim topo__claim--mismatch' : 'topo__claim'}>
            项目自称：{claimed.acyclic === null ? '' : claimed.acyclic ? 'DAG 无环' : '含环'}
            {claimed.layer_count !== null ? ` · ${claimed.layer_count} 拓扑层` : ''}
            {mismatched ? (
              <>
                {' '}
                <strong>—— 与本次独立复算不一致</strong>
                （按该项目自身数据结构复算；⛔ 本站不改上游，仅并陈）
              </>
            ) : (
              <> —— 与独立复算一致</>
            )}
          </li>
        ) : (
          <li className="topo__claim">上游未自述无环/层数，仅列实测值</li>
        )}
      </ul>
    </li>
  );
}

export function ProjectFigure({ name }: { name: string }) {
  const { metrics } = loadMetrics();
  const entry = metrics?.projects.find((item) => item.name === name);
  const graphs = loadTopology().filter((graph) => graph.project === name);
  const unavailable = entry && entry.status !== 'ok';

  return (
    <>
      {entry && entry.figures.length > 0 ? (
        <>
          <p className="detail__lead prose">
            规模指标按 <strong>scope</strong> 分行（E1：多图项目不单值化）。「—」表示该 scope 无此项，
            ⛔ 不等于 0。
          </p>
          <ScopeTable entry={entry} instanceKey={name} />
        </>
      ) : (
        <p className="detail__note">
          {unavailable
            ? `规模指标：未采集（${entry?.status}${entry?.notes[0] ? ` —— ${entry.notes[0].slice(0, 70)}` : ''}）。`
            : '规模指标：尚无该项目的采集记录。'}
        </p>
      )}

      {graphs.length > 0 ? (
        <>
          <h3 className="topo__title">结构实测（构建期 headless 拓扑计算）</h3>
          <p className="detail__note">
            由本站构建期对项目公开的结构化数据独立复算，与项目自称并陈；⛔ 不替代项目自身结论。
          </p>
          <ul className="topo__list">
            {graphs.map((graph) => (
              <GraphFacts graph={graph} key={`${graph.project}-${graph.scope}`} />
            ))}
          </ul>
        </>
      ) : null}

      {entry ? (
        <details className="topo__source">
          <summary>数据出处与口径（可展开）</summary>
          <ul className="notes">
            <li>
              指标来源：{entry.collectability === 'A' ? '项目页的结构化 JSON（枚举计数）' : '项目页散文统计（经人工确认一次）'}
              ；分区 {SECTION_LABELS[entry.section]}
              {entry.version_self ? `；项目自称版本 ${entry.version_self}` : ''}。
            </li>
            <li>
              采集页面：<code>{entry.source.url}</code>
              {entry.source.fetched_at ? `（抓取于 ${entry.source.fetched_at}）` : ''}
            </li>
            <li>
              页面文本指纹：<code>{entry.source.text_sha256?.slice(0, 32) ?? '—'}…</code>
              （改版即变化，用于察觉口径确认是否过期）
            </li>
            <li>
              口径规范：任务留档 <code>specs/e-metrics-spec.md</code> v1.0（E1–E6 已裁）；完整聚合视图见{' '}
              <Link href="/stats">聚合页</Link>。
            </li>
          </ul>
        </details>
      ) : null}
    </>
  );
}
