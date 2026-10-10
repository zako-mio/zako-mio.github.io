import Link from 'next/link';

import { Term } from '@/components/Term';
import {
  METRIC_COLUMNS,
  SECTION_LABELS,
  SECTION_NOTES,
  annotateChartBars,
  groupBySection,
  type Chart,
  type MetricEntry,
  type MetricFigure,
  type Metrics,
} from '@/lib/metrics';

function Value({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    // ★ 批十五 W2-①：把 `title`（MDN 明列 a11y/触屏缺陷）换成术语解释层（button ＋ aria-describedby）。
    //   `className` 保留原 `mtable__na` 配色 ⇒ 观感不变，只换语义通道。
    return (
      <Term id="missing" className="mtable__na">
        —
      </Term>
    );
  }
  return <>{value.toLocaleString('en-US')}</>;
}

function ProjectCell({ entry, rowSpan }: { entry: MetricEntry; rowSpan: number }) {
  return (
    <th className="mtable__project" scope="row" rowSpan={rowSpan}>
      <Link href={`/works/${entry.name}`}>{entry.title ?? entry.name}</Link>
      <span className="mtable__meta">
        {/* ★ 批十五 W2-①：可采集性分级（A/B）由 `title` 换成解释层；`badge badge--level` 保外观。 */}
        <Term id="collectability" className="badge badge--level">
          {entry.collectability ?? '?'}
        </Term>
        {entry.version_self ? <span className="mtable__version">自称 {entry.version_self}</span> : null}
      </span>
    </th>
  );
}

function SectionTable({
  section,
  entries,
  linked,
}: {
  section: keyof typeof SECTION_LABELS;
  entries: MetricEntry[];
  /** ★ 批十七 W4-③：本区里**有对应图表条**的项目名集合（`data-project` 只打在这些行上）。 */
  linked: Set<string>;
}) {
  return (
    <div className="mtable__block">
      <h3 className="mtable__title">{SECTION_LABELS[section]}</h3>
      <p className="mtable__note">{SECTION_NOTES[section]}</p>
      <div className="mtable__scroll">
        <table className="mtable">
          <caption className="sr-only">{SECTION_LABELS[section]}的规模指标</caption>
          <thead>
            <tr>
              <th scope="col">项目</th>
              <th scope="col">scope（图/视图）</th>
              {METRIC_COLUMNS.map((column) => (
                <th className="mtable__num" scope="col" key={column.key}>
                  <Term id={column.key}>{column.label}</Term>
                </th>
              ))}
              <th scope="col">取值来源</th>
            </tr>
          </thead>
          <tbody>
            {entries.flatMap((entry) => {
              if (entry.figures.length === 0) {
                return [
                  <tr
                    key={`${entry.name}-empty`}
                    data-project={linked.has(entry.name) ? entry.name : undefined}
                  >
                    <ProjectCell entry={entry} rowSpan={1} />
                    <td colSpan={METRIC_COLUMNS.length + 1}>
                      <span className="mtable__na">
                        未采集（{entry.status}
                        {entry.notes[0] ? `：${entry.notes[0].slice(0, 60)}` : ''}）
                      </span>
                    </td>
                  </tr>,
                ];
              }
              return entry.figures.map((figure: MetricFigure, index: number) => (
                <tr
                  key={`${entry.name}-${figure.scope}`}
                  data-project={linked.has(entry.name) ? entry.name : undefined}
                >
                  {index === 0 ? <ProjectCell entry={entry} rowSpan={entry.figures.length} /> : null}
                  <td className="mtable__scope">{figure.scope}</td>
                  {METRIC_COLUMNS.map((column) => (
                    <td className="mtable__num" key={column.key}>
                      <Value value={figure[column.key]} />
                    </td>
                  ))}
                  {index === 0 ? (
                    <td className="mtable__src" rowSpan={entry.figures.length}>
                      <a href={entry.source.url} rel="noreferrer noopener" target="_blank">
                        项目页
                      </a>
                      <span className="mtable__prov">{figure.provenance === 'prose' ? '散文' : 'JSON 枚举'}</span>
                    </td>
                  ) : null}
                </tr>
              ));
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** 内联双模 SVG：浅/深各一份，由 CSS 按三态主题切换；深色版对读屏隐藏以防重复朗读。 */
export function ChartFigure({ chart }: { chart: Chart }) {
  // ★ 批十七 W4-③：每个数据条打上 `data-project`（按 `rows[i].full`，⛔ 不按下标——
  //   图按值升序、表按目录序，两个集合同源但不同序）。注解只加在**渲染期**，⛔ `charts.json` 不变。
  const light = annotateChartBars(chart.svg.light, chart.rows);
  const dark = annotateChartBars(chart.svg.dark, chart.rows);
  return (
    <figure className="chart" id={`chart-${chart.key}`}>
      <figcaption className="chart__caption">{chart.title}</figcaption>
      <div
        className="chart__frame"
        data-spotlight="base"
        role="img"
        aria-label={`${chart.title}。数值与口径见上表；图为量级概览，不作复杂度排序。`}
        dangerouslySetInnerHTML={{ __html: light }}
      />
      <div
        className="chart__frame chart__frame--dark"
        data-spotlight="base"
        aria-hidden="true"
        dangerouslySetInnerHTML={{ __html: dark }}
      />
      <p className="chart__note">{chart.note}</p>
    </figure>
  );
}

export function MetricsDashboard({ metrics, charts }: { metrics: Metrics; charts: Chart[] }) {
  const groups = groupBySection(metrics);
  const unavailable = metrics.projects.filter((entry) => entry.status !== 'ok');
  // ★ 批十七 W4-③：图表 ↔ 表格联动的作用面 —— **有对应图表条**的项目才打 `data-project`。
  //   ⛔ 不给全表打：文档集群区/论文库区/未分区没有图，打了就会出现「悬停表格行却什么也不发生」，
  //      属「看起来有联动其实没有」⇒ 违反轴 B（所见符合所得）。
  const linked = new Set(charts.flatMap((chart) => chart.rows.map((row) => row.full)));

  return (
    <div className="mdash">
      <p className="mdash__asof">
        数据 <code>as_of {metrics.as_of}</code>（采集于项目页，每日管道重采）· 口径规范 v1.0（E1–E6 已裁）·
        {metrics.project_total} 项中 {metrics.project_total - unavailable.length} 项可采
      </p>

      {charts.map((chart) => (
        <ChartFigure chart={chart} key={chart.key} />
      ))}

      {groups.map((group) => (
        <SectionTable entries={group.entries} key={group.section} linked={linked} section={group.section} />
      ))}

      <ul className="notes">
        <li>
          <strong>⛔ 不跨区并比</strong>：DAG 图谱 / 文档集群 / 论文库三种交付形态的量纲不同，各区自成表；
          须比较时只可<strong>同 scope 对同 scope</strong>（E1/E3）。
        </li>
        <li>
          <strong>「—」不等于 0</strong>：空缺表示该 scope 无此项指标（E5）。语义上 0 与「无」不同，
          故此处不写 0。
        </li>
        <li>
          <strong>拓扑层 ≠ 学习阶段</strong>：前者是图论分层（最长路径），后者是教学分期；二者分列，
          混列会让「层数多者更复杂」成为假结论（E2）。
        </li>
        <li>
          规模数字取自各项目<strong>页面自称</strong>的统计区块或结构化 JSON（A 级枚举、B 级散文），
          与上游项目内容变更同步；数值经人工逐条确认一次，页面文本哈希已登记，改版后可察觉（E4）。
        </li>
        <li>
          本页<strong>不解读为难度或价值排序</strong>：不同项目对「实体」的用词与口径不同
          （包 / 插件节点 / 知识点 / 方法节点…）。
        </li>
        {unavailable.length > 0 ? (
          <li>
            <strong>未采集项</strong>：{unavailable.map((entry) => entry.name).join('、')}
            —— 未纳入当前口径规范的项目集，按 E5 显式标为不可采，⛔ 不猜测、不当作 0。
          </li>
        ) : null}
      </ul>
    </div>
  );
}
