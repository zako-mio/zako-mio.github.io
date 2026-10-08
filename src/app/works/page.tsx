import type { Metadata } from 'next';

import { WorksExplorer } from '@/components/WorksExplorer';
import { loadCatalog } from '@/lib/catalog';

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
          <h2 className="section__title">作品</h2>
          <p className="section__subtitle">
            全量索引 · 筛选与排序状态会写入地址栏，可直接分享
          </p>
        </header>

        {ok && projects.length > 0 ? (
          <WorksExplorer projects={projects} />
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
