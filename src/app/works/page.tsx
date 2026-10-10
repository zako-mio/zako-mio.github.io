import type { Metadata } from 'next';

import { WorksExplorer } from '@/components/WorksExplorer';
import { loadCatalog } from '@/lib/catalog';
import { recencyRangeOf } from '@/lib/recency';

export const metadata: Metadata = {
  title: '作品',
  description: '全部开源作品的索引：按类型、领域与语言筛选，或搜索关键词。',
  alternates: { canonical: '/works' },
};

export default function WorksPage() {
  const { projects, generatedAt, ok, hint } = loadCatalog();

  return (
    <section className="section">
      <div className="container">
        <header className="section__head">
          <h1 className="section__title">作品</h1>
          <p className="section__subtitle">
            全量索引 · 筛选与排序状态会写入地址栏，可直接分享
          </p>
        </header>

        {/* ★ 批十五 C1：A1 把本页标题由 h2 改为 h1 后，卡片标题仍是 h3 ⇒
           h1→h3 **跳级**（缺 h2）。此处补一个**视觉隐藏**的 h2 作为作品集合的语义标题，
           恢复 h1→h2→h3 的正确层级（`sr-only`：不改变观感，仅服务屏幕阅读器/辅助技术）。
           ⛔ 不把 `ProjectCard` 的 h3 改成 h2 —— 它同时用于首页与详情页，那里 h2→h3 本就正确。 */}
        <h2 className="sr-only">全部作品</h2>

        {ok && projects.length > 0 ? (
          <WorksExplorer projects={projects} range={recencyRangeOf(projects)} />
        ) : (
          <p className="empty-state">{hint ?? '暂无项目数据。'}</p>
        )}

        {generatedAt ? (
          <p className="page__footnote">数据 as_of {generatedAt.slice(0, 10)} · 每日管道重生成</p>
        ) : null}
      </div>
    </section>
  );
}
