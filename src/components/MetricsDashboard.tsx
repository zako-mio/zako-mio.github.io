import Link from 'next/link';

import {
  METRIC_COLUMNS,
  SECTION_LABELS,
  SECTION_NOTES,
  groupBySection,
  type Chart,
  type MetricEntry,
  type MetricFigure,
  type Metrics,
} from '@/lib/metrics';

function Value({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return (
      <span className="mtable__na" title="该 scope 无此项（E5：缺失留空，不等于 0）">
        —
      </span>
    );
  }
  return <>{value.toLocaleString('en-US')}</>;
}

function ProjectCell({ entry, rowSpan }: { entry: MetricEntry; rowSpan: number }) {
  return (
    <th className="mtable__project" scope="row" rowSpan={rowSpan}>
      <Link href={`/works/${entry.name}`}>{entry.title ?? entry.name}</Link>
      <span className="mtable__meta">
        <span className={`badge badge--level`} title={entry.collectability === 'A' ? '页面暴露结构化 JSON，可精确枚举' : '仅页面散文数字，经人工确认'}>
          {entry.collectability ?? '?'}
        </span>
        {entry.version_self ? <span className="mtable__version">自称 {entry.version_self}</span> : null}
      </span>
    </th>
  );
}

function SectionTable({ section, entries }: { section: keyof typeof SECTION_LABELS; entries: MetricEntry[] }) {
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
                <th className="mtable__num" scope="col" key={column.key} title={column.hint}>
                  {column.label}
                </th>
              ))}
              <th scope="col">取值来源</th>
            </tr>
          </thead>
          <tbody>
            {entries.flatMap((entry) => {
              if (entry.figures.length === 0) {
                return [
                  <tr key={`${entry.name}-empty`}>
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
                <tr key={`${entry.name}-${figure.scope}`}>
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
  return (
    <figure className="chart" id={`chart-${chart.key}`}>
      <figcaption className="chart__caption">{chart.title}</figcaption>
      <div
        className="chart__frame"
        role="img"
        aria-label={`${chart.title}。数值与口径见上表；图为量级概览，不作复杂度排序。`}
        dangerouslySetInnerHTML={{ __html: chart.svg.light }}
      />
      <div
        className="chart__frame chart__frame--dark"
        aria-hidden="true"
        dangerouslySetInnerHTML={{ __html: chart.svg.dark }}
      />
      <p className="chart__note">{chart.note}</p>
    </figure>
  );
}

export function MetricsDashboard({ metrics, charts }: { metrics: Metrics; charts: Chart[] }) {
  const groups = groupBySection(metrics);
  const unavailable = metrics.projects.filter((entry) => entry.status !== 'ok');

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
        <SectionTable entries={group.entries} key={group.section} section={group.section} />
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
