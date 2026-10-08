import Link from 'next/link';

import { PROFILE_GROUPS, PROFILE_LEAD } from '@/lib/profile';
import type { DerivedStats } from '@/lib/catalog';

export interface ProfileAboutProps {
  stats: DerivedStats;
  compact?: boolean;
}

export function ProfileAbout({ stats, compact = false }: ProfileAboutProps) {
  const overview = [
    { key: '技术方向', value: PROFILE_GROUPS[1].items.join(' / ') },
    { key: '活跃仓库', value: `${stats.projectCount} 个` },
    { key: '最近更新', value: stats.latestPush ? stats.latestPush.slice(0, 10) : '—' },
  ];

  return (
    <section id="about" className={compact ? 'section section--tight' : 'section'}>
      <div className="container">
        <header className="section__head">
          <h2 className="section__title">关于</h2>
          <p className="section__subtitle">匿名技术画像 · 只呈现方向与作品</p>
        </header>

        <div className="about__grid">
          <div className="about__main">
            <p className="about__lead prose">{PROFILE_LEAD}</p>

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
          </div>

          <aside className="about__overview" aria-label="速览">
            <h3 className="about__overview-title">速览</h3>
            <dl className="overview">
              {overview.map((row) => (
                <div className="overview__row" key={row.key}>
                  <dt className="overview__key">{row.key}</dt>
                  <dd className="overview__val">{row.value}</dd>
                </div>
              ))}
            </dl>
            {!compact ? (
              <p className="about__more">
                <Link href="/about">完整画像与工作方式 →</Link>
              </p>
            ) : null}
          </aside>
        </div>
      </div>
    </section>
  );
}
