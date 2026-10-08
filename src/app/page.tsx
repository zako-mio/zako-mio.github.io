import Link from 'next/link';

import { Contact } from '@/components/Contact';
import { Hero } from '@/components/Hero';
import { ProfileAbout } from '@/components/ProfileAbout';
import { ProjectCard } from '@/components/ProjectCard';
import { StatsBar } from '@/components/StatsBar';
import { WorksExplorer } from '@/components/WorksExplorer';
import { deriveStats, loadCatalog } from '@/lib/catalog';
import { loadSiteConfig, SITE_TAGLINE } from '@/lib/site';

const siteConfig = loadSiteConfig();

export default function HomePage() {
  const { projects, generatedAt, ok, hint } = loadCatalog();
  const stats = deriveStats(projects);
  const github = `https://github.com/${siteConfig.owner}`;
  const featured = projects.filter((project) => project.featured);
  const hasProjects = ok && projects.length > 0;

  return (
    <>
      <Hero displayName={siteConfig.display_name} tagline={SITE_TAGLINE} github={github} />

      {hasProjects ? <StatsBar stats={stats} generatedAt={generatedAt} /> : null}

      {featured.length > 0 ? (
        <section id="featured" className="section">
          <div className="container">
            <header className="section__head">
              <h2 className="section__title">主线作品</h2>
              <p className="section__subtitle">三条最完整的作品线 · 每项都有站内详情页</p>
            </header>
            <div className="projects-grid">
              {featured.map((project) => (
                <ProjectCard project={project} key={project.name} />
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <section id="works" className="section">
        <div className="container">
          <header className="section__head">
            <h2 className="section__title">全部作品</h2>
            <p className="section__subtitle">
              按类型、领域与语言筛选，或直接搜索关键词 ·{' '}
              <Link className="section__link" href="/works">
                独立索引页 →
              </Link>
            </p>
          </header>

          {hasProjects ? (
            <WorksExplorer projects={projects} />
          ) : (
            <p className="empty-state">{hint ?? '暂无项目数据。'}</p>
          )}
        </div>
      </section>

      <ProfileAbout stats={stats} compact />
      <Contact email={siteConfig.contact_email} github={github} />
    </>
  );
}
