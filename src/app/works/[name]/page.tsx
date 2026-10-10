import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { Disclosure } from '@/components/Disclosure';
import { ProjectCard } from '@/components/ProjectCard';
import { ProjectFigure } from '@/components/ProjectFigure';
import { TocSidebar, type TocItem } from '@/components/TocSidebar';
import { loadCatalog } from '@/lib/catalog';
import { recencyRangeOf } from '@/lib/recency';
import { DOMAIN_LABELS, TYPE_LABELS } from '@/lib/schema';

export const dynamicParams = false;

export function generateStaticParams() {
  const { projects } = loadCatalog();
  return projects.map((project) => ({ name: project.name }));
}

type PageProps = { params: Promise<{ name: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { name } = await params;
  const { projects } = loadCatalog();
  const project = projects.find((item) => item.name === name);
  if (!project) return { title: '未找到项目' };
  return {
    title: project.title,
    description: project.summary,
    alternates: { canonical: `/works/${project.name}` },
  };
}

/**
 * 详情页骨架（T2 指标卡式 + T4 图谱式结构位）。
 *
 * ★ 第一批只呈现**可核实的既有数据**（项目索引字段 + 派生指标 + 关联项目），
 *   ⛔ 不编造「设计要点 / 难点」等尚未产出的内容。
 * ★ 第二批补：该项目自己的 DAG 嵌入、设计与实现要点、证据链区块。
 */
export default async function ProjectPage({ params }: PageProps) {
  const { name } = await params;
  const { projects } = loadCatalog();
  const project = projects.find((item) => item.name === name);
  if (!project) notFound();

  // 卡片标尺的共享跨度：算一次给全部同类卡（纯函数，不取数）
  const range = recencyRangeOf(projects);

  const typeLabel = TYPE_LABELS[project.type];
  const domainLabels = project.domains.map((domain) => DOMAIN_LABELS[domain]);

  const related = projects
    .filter((item) => item.name !== project.name)
    .map((item) => ({
      project: item,
      shared: item.domains.filter((domain) => project.domains.includes(domain)),
    }))
    .filter((entry) => entry.shared.length > 0)
    .sort((a, b) => b.shared.length - a.shared.length)
    .slice(0, 3);

  const metrics = [
    { key: '类型', value: typeLabel },
    { key: '领域', value: domainLabels.join(' / ') },
    { key: '主要语言', value: project.language ?? '未标注' },
    { key: '星标', value: typeof project.stars === 'number' ? String(project.stars) : '—' },
    { key: '最近推送', value: project.pushed_at ? project.pushed_at.slice(0, 10) : '—' },
    { key: '交付形态', value: project.has_pages ? 'GitHub Pages 在线预览' : '仅仓库' },
  ];

  const toc: TocItem[] = [
    { id: 'overview', label: '概览' },
    { id: 'summary', label: '项目摘要' },
    ...(related.length > 0 ? [{ id: 'related', label: '关联项目' }] : []),
    ...(project.has_pages ? [{ id: 'figure', label: '该项目图谱' }] : []),
    { id: 'links', label: '入口' },
  ];

  return (
    <div className="container detail">
      <nav className="breadcrumb" aria-label="面包屑">
        <Link href="/works">作品</Link>
        <span aria-hidden="true">/</span>
        <span>{project.name}</span>
      </nav>

      <div className="detail__layout">
        <article className="detail__main">
          <header className="detail__head">
            <ul className="taglist">
              <li className="chip chip--type" data-spotlight="micro">{typeLabel}</li>
              {domainLabels.map((label) => (
                <li className="chip" data-spotlight="micro" key={label}>
                  {label}
                </li>
              ))}
              {!project.has_pages ? <li className="chip chip--warning" data-spotlight="micro">仅仓库</li> : null}
            </ul>
            <h1 className="detail__title">{project.title}</h1>
            <p className="detail__summary prose">{project.summary}</p>
          </header>

          <section id="overview" className="detail__section">
            <h2 className="detail__section-title">概览</h2>
            <dl className="metrics">
              {metrics.map((metric) => (
                <div className="metrics__item" data-spotlight="soft" key={metric.key}>
                  <dt className="metrics__key">{metric.key}</dt>
                  <dd className="metrics__value">{metric.value}</dd>
                </div>
              ))}
            </dl>
            <p className="detail__note">
              以上指标来自项目索引的零成本派生量，非人工填写。规模类指标（节点 / 边 / 分组）
              需从各项目页面抽取，属第二批口径规范后的采集范围。
            </p>
          </section>

          <section id="summary" className="detail__section">
            <h2 className="detail__section-title">项目摘要</h2>
            <Disclosure summary="摘要的取数口径" hint="可展开">
              <p>
                摘要取自项目仓库的公开描述（`site.config.json` 的
                <code> summary_source = description_first </code>
                口径），由每日管道重生成；仓库描述变更会在下一次构建体现。
              </p>
            </Disclosure>
          </section>

          {related.length > 0 ? (
            <section id="related" className="detail__section">
              <h2 className="detail__section-title">关联项目</h2>
              <p className="detail__lead">按共享领域数量排序。</p>
              <ul className="related__list">
                {related.map(({ project: item, shared }) => (
                  <li className="related__item" data-spotlight="soft" key={item.name}>
                    <Link className="related__link" href={`/works/${item.name}`}>
                      {item.title}
                    </Link>
                    <span className="related__shared">
                      共享领域：{shared.map((domain) => DOMAIN_LABELS[domain]).join(' · ')}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {project.has_pages ? (
            <section id="figure" className="detail__section">
              <h2 className="detail__section-title">该项目图谱</h2>
              <ProjectFigure name={project.name} />
              <p className="detail__note">
                图的可交互真身在项目站内（本站只呈现可机读的规模与结构数据，故无 JS 亦可读）。
              </p>
              <p>
                <a
                  className="button button--small"
                  href={project.entry_url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  打开该项目图谱 ↗
                </a>
              </p>
            </section>
          ) : null}

          <section id="links" className="detail__section">
            <h2 className="detail__section-title">入口</h2>
            <ul className="contact__list">
              {project.has_pages ? (
                <li>
                  <a
                    className="contact__link"
                    data-spotlight="soft"
                    href={project.entry_url}
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    <span className="contact__k">在线预览</span>
                    <span className="contact__v">{project.entry_url.replace(/^https?:\/\//, '')}</span>
                  </a>
                </li>
              ) : null}
              <li>
                <a
                  className="contact__link"
                  data-spotlight="soft"
                  href={project.repo_url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  <span className="contact__k">仓库</span>
                  <span className="contact__v">{project.repo_url.replace(/^https?:\/\//, '')}</span>
                </a>
              </li>
            </ul>
          </section>
        </article>

        <aside className="detail__aside">
          <TocSidebar items={toc} />
        </aside>
      </div>

      {related.length > 0 ? (
        <section className="detail__next">
          <h2 className="detail__section-title">同类作品</h2>
          <div className="projects-grid">
            {related.map(({ project: item }) => (
              <ProjectCard project={item} key={item.name} range={range} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
