import Link from 'next/link';

export interface HeroProps {
  displayName: string;
  tagline: string;
  github: string;
}

/**
 * Hero。
 *
 * ★ 本轮去重：原 Astro 版同时有 `hero__actions`（3 个按钮）与 `hero__quick`（同一组
 *   3 个链接的第二份），首屏出现两组指向相同目标的入口。现只保留一组主 CTA，
 *   跨页跳转交给顶部导航。
 */
export function Hero({ displayName, tagline, github }: HeroProps) {
  return (
    <section id="top" className="hero">
      <div className="container hero__inner">
        <p className="hero__eyebrow">数据科学 × AI Agent 工程</p>
        <h1 className="hero__title">{displayName}</h1>
        <p className="hero__tagline prose">{tagline}</p>
        <ul className="hero__actions">
          <li>
            <Link className="button button--primary" href="/works">
              浏览作品
            </Link>
          </li>
          <li>
            <Link className="button" href="/stats">
              聚合视图
            </Link>
          </li>
          <li>
            <a className="button" href={github} rel="noopener noreferrer" target="_blank">
              GitHub
            </a>
          </li>
        </ul>
      </div>
    </section>
  );
}
