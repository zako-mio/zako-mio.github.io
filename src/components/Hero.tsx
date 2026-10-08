import Link from 'next/link';

export interface HeroProps {
  displayName: string;
  tagline: string;
}

/**
 * Hero。
 *
 * ★ 本轮（第三批）收敛入口：原先 Hero 的按钮组与「站点分区」区块指向同样的目标
 *   （`/works`、`/stats`、GitHub），同一批入口在首屏出现了两遍。现 Hero 只留
 *   **一个主 CTA**，其余入口交给下方「站点分区」（每页写明它回答什么问题）。
 */
export function Hero({ displayName, tagline }: HeroProps) {
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
        </ul>
      </div>
    </section>
  );
}
