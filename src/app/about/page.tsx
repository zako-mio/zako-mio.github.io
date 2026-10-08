import type { Metadata } from 'next';
import Link from 'next/link';

import { Disclosure } from '@/components/Disclosure';
import { TocSidebar, type TocItem } from '@/components/TocSidebar';
import { deriveStats, loadCatalog } from '@/lib/catalog';
import { PROFILE_GROUPS, PROFILE_LEAD } from '@/lib/profile';
import { loadSiteConfig, SITE_TAGLINE } from '@/lib/site';

export const metadata: Metadata = {
  title: '关于',
  description: '匿名技术画像、工作方式与本页的证据约定。',
  alternates: { canonical: '/about' },
};

const TOC: TocItem[] = [
  { id: 'portrait', label: '技术画像' },
  { id: 'directions', label: '方向与兴趣' },
  { id: 'practice', label: '工作方式' },
  { id: 'anonymity', label: '关于匿名' },
  { id: 'contact', label: '联系' },
];

const PRACTICE = [
  '单一真相源 + 派生：能派生的数字不手抄，改了源就重生成。',
  '可复现优先：结论要能回源，取证件与门控随产物一起留档。',
  '先定口径再采数：术语不一致时先写规范，宁可空着也不拼凑可比性。',
  '原型先于讨论：聊不拢的地方就出一个能跑的样张。',
];

export default function AboutPage() {
  const siteConfig = loadSiteConfig();
  const { projects } = loadCatalog();
  const stats = deriveStats(projects);
  const github = `https://github.com/${siteConfig.owner}`;

  return (
    <div className="container detail">
      <header className="detail__head">
        <h1 className="detail__title">关于</h1>
        <p className="detail__summary prose">{SITE_TAGLINE}</p>
      </header>

      <div className="detail__layout">
        <article className="detail__main">
          <section id="portrait" className="detail__section">
            <h2 className="detail__section-title">技术画像</h2>
            <p className="detail__lead prose">{PROFILE_LEAD}</p>
            <dl className="metrics">
              <div className="metrics__item">
                <dt className="metrics__key">公开作品</dt>
                <dd className="metrics__value">{stats.projectCount}</dd>
              </div>
              <div className="metrics__item">
                <dt className="metrics__key">领域覆盖</dt>
                <dd className="metrics__value">{stats.domainCounts.length}</dd>
              </div>
              <div className="metrics__item">
                <dt className="metrics__key">最近更新</dt>
                <dd className="metrics__value">{stats.latestPush?.slice(0, 10) ?? '—'}</dd>
              </div>
            </dl>
          </section>

          <section id="directions" className="detail__section">
            <h2 className="detail__section-title">方向与兴趣</h2>
            <div className="about__blocks">
              {PROFILE_GROUPS.map((group) => (
                <div className="about__block" key={group.key}>
                  <h3 className="about__label">{group.label}</h3>
                  <ul className="taglist">
                    {group.items.map((item) => (
                      <li className="chip" key={item}>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          <section id="practice" className="detail__section">
            <h2 className="detail__section-title">工作方式</h2>
            <ul className="notes notes--plain">
              {PRACTICE.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <Disclosure summary="这些原则怎么体现在本站里" hint="可展开">
              <ul className="notes notes--plain">
                <li>项目索引由每日管道从仓库取数生成，不在页面上手抄。</li>
                <li>页脚暴露数据时间戳与构建号，用于判断内容新鲜度与回退。</li>
                <li>
                  聚合页明确区分「已可算的指标」与「口径未定、暂不呈现的指标」，不把缺口
                  包装成结论。
                </li>
              </ul>
            </Disclosure>
          </section>

          <section id="anonymity" className="detail__section">
            <h2 className="detail__section-title">关于匿名</h2>
            <p className="detail__lead prose">
              本站以匿名方式呈现：不出现姓名、单位、地域等可实名定位的字段。
              作品集的分量来自作品本身，而不是履历。
            </p>
          </section>

          <section id="contact" className="detail__section">
            <h2 className="detail__section-title">联系</h2>
            <ul className="contact__list">
              <li>
                <a className="contact__link" href={`mailto:${siteConfig.contact_email}`}>
                  <span className="contact__k">邮箱</span>
                  <span className="contact__v">{siteConfig.contact_email}</span>
                </a>
              </li>
              <li>
                <a className="contact__link" href={github} rel="noopener noreferrer" target="_blank">
                  <span className="contact__k">GitHub</span>
                  <span className="contact__v">{github.replace(/^https?:\/\//, '')}</span>
                </a>
              </li>
            </ul>
            <p className="detail__note">
              也可以直接 <Link href="/works">浏览作品</Link> 或 <Link href="/stats">看聚合视图</Link>。
            </p>
          </section>
        </article>

        <aside className="detail__aside">
          <TocSidebar items={TOC} />
        </aside>
      </div>
    </div>
  );
}
