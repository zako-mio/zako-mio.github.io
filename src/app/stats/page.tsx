import type { Metadata } from 'next';
import Link from 'next/link';

import { TocSidebar, type TocItem } from '@/components/TocSidebar';
import { MetricsDashboard } from '@/components/MetricsDashboard';
import { deriveStats, loadCatalog } from '@/lib/catalog';
import { loadCharts, loadMetrics } from '@/lib/metrics';
import { DOMAIN_LABELS, TYPE_LABELS, type ProjectDomain, type ProjectType } from '@/lib/schema';

export const metadata: Metadata = {
  title: '聚合',
  description: '项目索引的聚合视图：规模指标（E）、类型、领域、语言分布与更新时间线。',
  alternates: { canonical: '/stats' },
};

const TOC: TocItem[] = [
  { id: 'overview', label: '总览' },
  { id: 'scale', label: '规模指标' },
  { id: 'types', label: '类型分布' },
  { id: 'domains', label: '领域分布' },
  { id: 'languages', label: '语言分布' },
  { id: 'timeline', label: '更新时间线' },
  { id: 'caveats', label: '口径与边界' },
];

function BarList({
  rows,
  labelOf,
}: {
  rows: Array<{ value: string; count: number }>;
  labelOf?: (value: string) => string;
}) {
  const max = rows.reduce((peak, row) => Math.max(peak, row.count), 0) || 1;
  return (
    <ul className="bars">
      {rows.map((row) => (
        <li className="bars__row" key={row.value}>
          <span className="bars__label">{labelOf ? labelOf(row.value) : row.value}</span>
          <span className="bars__track">
            <span className="bars__fill" style={{ width: `${(row.count / max) * 100}%` }} />
          </span>
          <span className="bars__count">{row.count}</span>
        </li>
      ))}
    </ul>
  );
}

export default function StatsPage() {
  const { projects, generatedAt, ok, hint } = loadCatalog();
  const stats = deriveStats(projects);
  const { metrics, ok: metricsOk, hint: metricsHint } = loadMetrics();
  const charts = loadCharts();

  if (!ok || projects.length === 0) {
    return (
      <section className="section">
        <div className="container">
          <h1 className="detail__title">聚合</h1>
          <p className="empty-state">{hint ?? '暂无项目数据。'}</p>
        </div>
      </section>
    );
  }

  const timeline = [...projects]
    .filter((project) => project.pushed_at)
    .sort((a, b) => (b.pushed_at ?? '').localeCompare(a.pushed_at ?? ''));

  return (
    <div className="container detail">
      <header className="detail__head">
        <h1 className="detail__title">聚合</h1>
        <p className="detail__summary prose">
          项目索引的分布与时间视图。所有数字均由 <code>projects.json</code> 零成本派生，
          无外部采集、无运行期请求。
        </p>
      </header>

      <div className="detail__layout">
        <article className="detail__main">
          <section id="overview" className="detail__section">
            <h2 className="detail__section-title">总览</h2>
            <dl className="metrics">
              <div className="metrics__item" data-spotlight="soft">
                <dt className="metrics__key">项目总数</dt>
                <dd className="metrics__value">{stats.projectCount}</dd>
              </div>
              <div className="metrics__item" data-spotlight="soft">
                <dt className="metrics__key">主线作品</dt>
                <dd className="metrics__value">{stats.featuredCount}</dd>
              </div>
              <div className="metrics__item" data-spotlight="soft">
                <dt className="metrics__key">类型数</dt>
                <dd className="metrics__value">{stats.typeCounts.length}</dd>
              </div>
              <div className="metrics__item" data-spotlight="soft">
                <dt className="metrics__key">领域数</dt>
                <dd className="metrics__value">{stats.domainCounts.length}</dd>
              </div>
              <div className="metrics__item" data-spotlight="soft">
                <dt className="metrics__key">最近推送</dt>
                <dd className="metrics__value">{stats.latestPush?.slice(0, 10) ?? '—'}</dd>
              </div>
              <div className="metrics__item" data-spotlight="soft">
                <dt className="metrics__key">最早推送</dt>
                <dd className="metrics__value">{stats.earliestPush?.slice(0, 10) ?? '—'}</dd>
              </div>
            </dl>
          </section>

          <section id="scale" className="detail__section">
            <h2 className="detail__section-title">规模指标</h2>
            {metricsOk && metrics ? (
              <MetricsDashboard charts={charts} metrics={metrics} />
            ) : (
              <p className="empty-state">{metricsHint ?? '暂无规模指标。'}</p>
            )}
          </section>

          <section id="types" className="detail__section">
            <h2 className="detail__section-title">类型分布</h2>
            <BarList rows={stats.typeCounts} labelOf={(value) => TYPE_LABELS[value as ProjectType] ?? value} />
          </section>

          <section id="domains" className="detail__section">
            <h2 className="detail__section-title">领域分布</h2>
            <p className="detail__note">一个项目可属多个领域，故计数之和大于项目总数。</p>
            <BarList
              rows={stats.domainCounts}
              labelOf={(value) => DOMAIN_LABELS[value as ProjectDomain] ?? value}
            />
          </section>

          <section id="languages" className="detail__section">
            <h2 className="detail__section-title">语言分布</h2>
            <BarList rows={stats.languageCounts} />
          </section>

          <section id="timeline" className="detail__section">
            <h2 className="detail__section-title">更新时间线</h2>
            <ul className="timeline">
              {timeline.map((project) => (
                <li className="timeline__row" key={project.name}>
                  <span className="timeline__date">{project.pushed_at?.slice(0, 10)}</span>
                  <Link className="timeline__link" href={`/works/${project.name}`}>
                    {project.title}
                  </Link>
                  <span className="timeline__meta">{TYPE_LABELS[project.type]}</span>
                </li>
              ))}
            </ul>
          </section>

          <section id="caveats" className="detail__section">
            <h2 className="detail__section-title">口径与边界</h2>
            <ul className="notes">
              <li>
                所有计数来自 <code>src/data/projects.json</code>（每日管道重生成），本页数字带
                <code> as_of </code>，⛔ 不得当作现态。
              </li>
              <li>
                <strong>规模类指标（节点数 / 边数 / 分组数 / 版本）已纳入上表</strong>：口径由
                <code> specs/e-metrics-spec.md </code>v1.0 裁定（E1–E6），采集后经用户逐条人工确认并登记
                页面文本哈希；⛔ 不与「项目总数」这类计数混算，也不跨形态并比。
              </li>
              <li>
                「最近推送」是仓库同步时间，<strong>不等于</strong>项目在建时间；通道每日运行，
                若项目无真实变更，该字段仍会随同步刷新。
              </li>
              <li>本页不呈现「总星标」作为主指标：其量级小，作为人气指标会误导。</li>
            </ul>
            {generatedAt ? <p className="page__footnote">数据 as_of {generatedAt.slice(0, 10)}</p> : null}
          </section>
        </article>

        <aside className="detail__aside">
          <TocSidebar items={TOC} />
        </aside>
      </div>
    </div>
  );
}
