import type { DerivedStats } from '@/lib/catalog';

export interface StatsBarProps {
  stats: DerivedStats;
  generatedAt?: string | null;
}

function formatDay(value: string | null): string {
  if (!value) return '—';
  return value.slice(0, 10);
}

/**
 * 聚合统计条（E 的最低成本兑现）。
 *
 * ★ 口径纪律：
 *   - 只呈现**零成本派生**指标（全部来自 projects.json 现成字段），不做任何外部采集；
 *   - 轨道类数字（节点/边/组/版本）属第二批 E 采集，本批不出现；
 *   - ⛔ 不呈现「总星标」作为主指标——其量级小，反而误导；星标只在中性位置弱展示；
 *   - 所有数字带 `as_of`，避免活值被读成现态。
 */
export function StatsBar({ stats, generatedAt = null }: StatsBarProps) {
  const items = [
    { key: '项目', value: String(stats.projectCount) },
    { key: '主线', value: String(stats.featuredCount) },
    { key: '类型', value: String(stats.typeCounts.length) },
    { key: '领域', value: String(stats.domainCounts.length) },
    { key: '语言', value: String(stats.languageCounts.length) },
    { key: '最近更新', value: formatDay(stats.latestPush) },
  ];

  return (
    <section className="stats" aria-label="项目聚合概览">
      <div className="container">
        <dl className="stats__grid">
          {items.map((item) => (
            <div className="stats__item" key={item.key}>
              <dt className="stats__key">{item.key}</dt>
              <dd className="stats__val">{item.value}</dd>
            </div>
          ))}
        </dl>
        <p className="stats__asof">
          指标口径：仅项目索引的零成本派生量
          {generatedAt ? <> · 数据 as_of {generatedAt.slice(0, 10)}</> : null}
          {' · '}
          <a href="/stats">查看聚合页</a>
        </p>
      </div>
    </section>
  );
}
