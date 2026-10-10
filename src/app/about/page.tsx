import type { Metadata } from 'next';
import Link from 'next/link';

import { Disclosure } from '@/components/Disclosure';
import { PracticeCycleFigure } from '@/components/figures/PracticeCycleFigure';
import { TocSidebar, type TocItem } from '@/components/TocSidebar';
import {
  PROFILE_FOCUS,
  PROFILE_GROUPS,
  PROFILE_LEAD,
  PROFILE_PRACTICE,
  PROFILE_ROLE,
  PROFILE_TIMELINE,
  PROFILE_TOOLKIT,
  PROFILE_WORKING_ON,
} from '@/lib/profile';
import { loadSiteConfig, SITE_TAGLINE } from '@/lib/site';

export const metadata: Metadata = {
  title: '关于',
  description: '匿名技术画像、工作方式与本页的证据约定。',
  alternates: { canonical: '/about' },
};

const TOC: TocItem[] = [
  { id: 'portrait', label: '技术画像' },
  { id: 'working-on', label: '近期在做' },
  { id: 'directions', label: '方向与兴趣' },
  { id: 'toolkit', label: '工具链' },
  { id: 'practice', label: '工作方式' },
  { id: 'timeline', label: '时间线' },
  { id: 'anonymity', label: '关于匿名' },
  { id: 'contact', label: '联系' },
];

export default function AboutPage() {
  const siteConfig = loadSiteConfig();
  const github = `https://github.com/${siteConfig.owner}`;

  return (
    <div className="container detail">
      <header className="detail__head">
        <h1 className="detail__title">关于</h1>
        <p className="detail__summary prose">{SITE_TAGLINE}</p>
      </header>

      <div className="detail__layout">
        <article className="detail__main">
          <section id="portrait" className="detail__section" data-reveal>
            <h2 className="detail__section-title">技术画像</h2>
            <p className="detail__lead prose">{PROFILE_LEAD}</p>

            <ul className="threads">
              <li className="threads__item">
                <span className="threads__key">定位</span>
                <span className="threads__val">{PROFILE_ROLE}</span>
              </li>
              <li className="threads__item">
                <span className="threads__key">主线</span>
                <span className="threads__val">开源实践 · 可复现的工程体系</span>
              </li>
              <li className="threads__item">
                <span className="threads__key">方式</span>
                <span className="threads__val">把业务问题翻译成数据与算法问题，再交付结论</span>
              </li>
            </ul>

            <p className="detail__note">
              与数字有关的取值、口径与边界情况集中在 <Link href="/stats">聚合页</Link>，
              本页不复述，避免同一组数字出现第二处真相源。
            </p>
          </section>

          <section id="working-on" className="detail__section" data-reveal>
            <h2 className="detail__section-title">近期在做</h2>
            {/* 图形化编排：左侧一条贯穿的强调轨把三条串成「并行推进中」的一条带，
                ⛔ 不是三个并列的项目符号 —— 形状本身表达了「同一时期、三条线」。 */}
            <ul className="threads threads--rail">
              {PROFILE_WORKING_ON.map((item, index) => (
                <li className="threads__item" key={item}>
                  <span className="threads__mark" aria-hidden="true">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <span className="threads__val">{item}</span>
                </li>
              ))}
            </ul>
          </section>

          <section id="directions" className="detail__section" data-reveal>
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
            <p className="detail__note">
              左栏常驻的「关注方向」是这里的压缩视图（{PROFILE_FOCUS.join(' · ')}），
              两处同源，改一处即改两处。
            </p>
          </section>

          <section id="toolkit" className="detail__section" data-reveal>
            <h2 className="detail__section-title">工具链</h2>
            <div className="about__blocks">
              {PROFILE_TOOLKIT.map((group) => (
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

          <section id="practice" className="detail__section" data-reveal>
            <h2 className="detail__section-title">工作方式</h2>

            {/* ★ 四条原则的真实关系是**闭环**（口径错了要回炉、复盘产出下一轮口径）。
                并列列表会把「环」讲成「清单」，信息被抹平 ⇒ 这里先出图，文字作展开。 */}
            <figure className="figure" data-spotlight="base">
              <div className="figure__frame">
                <PracticeCycleFigure />
              </div>
              <figcaption className="figure__caption">
                四步不是并列而是闭环：复盘的结果回流成下一轮的口径修正。
                下面是每步的具体做法。
              </figcaption>
            </figure>

            <ul className="notes notes--plain">
              {PROFILE_PRACTICE.map((item) => (
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

          <section id="timeline" className="detail__section" data-reveal>
            <h2 className="detail__section-title">时间线</h2>
            {/* 图形化：用一条纵向脊线把年份串起来，层级由几何位置表达，
                ⛔ 不靠「第一、其次、最后」这类连接词分点。 */}
            <ol className="milestones">
              {PROFILE_TIMELINE.map((entry) => (
                <li className="milestones__item" key={entry.year}>
                  <span className="milestones__year">{entry.year}</span>
                  <span className="milestones__body">
                    <span className="milestones__title">{entry.title}</span>
                    <span className="milestones__note">{entry.note}</span>
                  </span>
                </li>
              ))}
            </ol>
            <p className="detail__note">
              只到年份粒度：更细的时间点会与可反查的公开记录对上，违背本站的匿名约定。
            </p>
          </section>

          <section id="anonymity" className="detail__section" data-reveal>
            <h2 className="detail__section-title">关于匿名</h2>
            <p className="detail__lead prose">
              本站以匿名方式呈现：不出现姓名、单位、地域等可实名定位的字段。
              作品集的分量来自作品本身，而不是履历。
            </p>
          </section>

          <section id="contact" className="detail__section" data-reveal>
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
