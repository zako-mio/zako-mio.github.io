import Link from 'next/link';

import { HeroPositionMap } from './figures/HeroPositionMap';

import { PROFILE_ROLE } from '@/lib/profile';

export interface HeroProps {
  displayName: string;
  tagline: string;
  /** 只有首页确实有「主线作品」区块时才渲染滚动提示 —— ⛔ 不留死锚点。 */
  hasFeatured?: boolean;
}

/**
 * Hero（第五批：加深氛围与图形层）。
 *
 * ★ 入口收敛沿用第三批的决定：Hero 只留**一个主 CTA**，
 *   其余入口交给下方「站点分区」（每页写明它回答什么问题）。
 * ★ 批八（裁决② V3）把右区从**装饰**升为**信息件**：`HeroPositionMap` 用 role="img"
 *   ＋ `<title>`/`<desc>` 重述 Hero 的定位陈述（复合背景 → 核心动作 → 三个方向），
 *   撤销了旧件的 `aria-hidden`；⛔ 仍不承载任何聚合数字，也不枚举作品。
 * ★ 进场动效由 CSS 关键帧驱动（`html.js-motion .hero__inner > *`），
 *   ⛔ 不依赖 JS 计算 ⇒ 首帧即开始，不出现「先静后动」的跳变。
 */
export function Hero({ displayName, tagline, hasFeatured = false }: HeroProps) {
  return (
    <section id="top" className="hero">
      <HeroPositionMap />
      <div className="container hero__inner">
        <p className="hero__eyebrow" data-spotlight="micro">{PROFILE_ROLE}</p>
        <h1 className="hero__title">{displayName}</h1>
        <p className="hero__tagline prose">{tagline}</p>
        <ul className="hero__actions">
          <li>
            <Link className="button button--primary" href="/works">
              浏览作品
            </Link>
          </li>
        </ul>

        {/* 几何化的「下面还有内容」提示（⛔ 不是又一个路由入口：
            它是页内锚点，不参与「同一批入口出现两遍」的那类重叠）。 */}
        {hasFeatured ? (
          <a className="hero__cue" href="#featured">
            <span className="hero__cue-rail" aria-hidden="true">
              <span className="hero__cue-dot" />
            </span>
            向下看主线
          </a>
        ) : null}
      </div>
    </section>
  );
}
