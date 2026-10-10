import { Hero } from '@/components/Hero';
import { ProjectCard } from '@/components/ProjectCard';
import { SiteBuildNotes } from '@/components/SiteBuildNotes';
import { SiteDirectory, type DirectoryItem } from '@/components/SiteDirectory';
import { loadCatalog } from '@/lib/catalog';
import { recencyRangeOf } from '@/lib/recency';
import { loadSiteConfig, SITE_TAGLINE } from '@/lib/site';

const siteConfig = loadSiteConfig();

/**
 * 分区清单（首页的枢纽职能）。
 *
 * ★ 纪律：本清单只写「这页回答什么问题」，⛔ 不复述任何分页的数字、区块或列表；
 *   每类内容只有一个落点（判据见 `scripts/gate_ia_division.py` A1–A5）。
 */
const DIRECTORY: DirectoryItem[] = [
  {
    href: '/works',
    label: '/works · 作品',
    question: '都有哪些作品',
    // ★ 批十七（V-A3＝B 的连带修正）：本条的 `note` 自身以「全量索引：」开头，
    //   而 `SiteDirectory` 的 `question`/`note` 分隔符同批由 `——` 改成了 `：`
    //   ⇒ 会撞成「都有哪些作品：全量索引：按类型…」的**双冒号**。
    //   ⇒ 把 `note` **内部**那一处改成 `·`（信息一字不减、去撞车；`·` 是本站既有分隔符）。
    note: '全量索引 · 按类型、领域与语言筛选，或直接搜索；筛选态写入地址栏可分享',
  },
  {
    href: '/stats',
    label: '/stats · 聚合',
    question: '数据的规模与口径边界是什么',
    note: '项目计数、规模指标（E）与分布时间线，逐项标注口径与不可采项',
  },
  {
    href: '/about',
    label: '/about · 关于',
    question: '这个人是谁、怎么工作、怎么联系',
    note: '技术画像、工作方式、匿名约定与联系方式',
  },
];

/**
 * 首页（第三批改版）。
 *
 * ★ 职能定位：回答「**这个人是谁、做什么、强在哪**」，不再陈列全部作品。
 *   - 上一版把 `WorksExplorer`（全量索引 ＋ 筛选器）整块嵌在首页，
 *     导致首页与 `/works` 的作品集合**完全相同**（实产物读数：10/10，差集为空；
 *     `/works` 的 93% 文本块出现在首页）。
 *   - 现按「每类内容唯一落点」重排：全量枚举 → `/works`；数字 → `/stats`；
 *     画像与联系 → `/about`；首页只留**定位 ＋ 精选代表作 ＋ 分区导航**。
 *   - ⛔ 精选名单仍是 `src/data/overrides.json` 的 `featured`（D10 已裁），
 *     首页只是它的呈现面之一，后续调整只改该文件。
 */
export default function HomePage() {
  const { projects, ok, hint } = loadCatalog();
  const github = `https://github.com/${siteConfig.owner}`;
  const featured = projects.filter((project) => project.featured);
  const hasProjects = ok && projects.length > 0;
  // 卡片标尺的共享跨度：服务端算一次，传给每张卡（⛔ 客户端不取数）
  const range = recencyRangeOf(projects);

  return (
    <>
      <Hero displayName={siteConfig.display_name} tagline={SITE_TAGLINE} hasFeatured={featured.length > 0} />

      {featured.length > 0 ? (
        <section id="featured" className="section" data-reveal>
          <div className="container">
            <header className="section__head">
              <h2 className="section__title">主线作品</h2>
              <p className="section__subtitle">
                三条最完整的作品线 · 每项都有站内详情页；全部作品的筛选索引在{' '}
                <a className="section__link" href="/works">
                  /works
                </a>
              </p>
            </header>
            <div className="projects-grid">
              {featured.map((project, index) => (
                <ProjectCard project={project} key={project.name} range={range} reveal index={index} />
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {!hasProjects ? (
        <section className="section">
          <div className="container">
            <p className="empty-state">{hint ?? '暂无项目数据。'}</p>
          </div>
        </section>
      ) : null}

      <SiteBuildNotes />

      <SiteDirectory items={DIRECTORY} github={github} />
    </>
  );
}
