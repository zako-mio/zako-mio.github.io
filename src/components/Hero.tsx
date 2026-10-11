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
 *
 * ★ 批二十点六：首屏左区加**个性化头像**，与定位陈述/名字/标语组成「身份簇」。
 *   三条纪律（每条都有实测或裁决依据，见 `report-batch20.6.md`）：
 *   ① **头像在名字左侧，⛔ 不在其上方** —— 本站批十九刚把 `.hero__eyebrow` 的
 *      「标题上方药丸标签」去壳（AI 味裁决 V-A5）；AI 味清单第 15–23 条含
 *      `Icon tile above heading` / `Badge above headline`。放**左侧**即绕开这一类命中。
 *   ② **形状＝正圆，且只此一解** —— 圆角方（squircle）在**两个主题下都**把素材
 *      左上角的插画白底暴露成一块白角（深色主题下尤其刺眼）；正圆把四角全裁掉，
 *      是唯一「主题无关」的形状。实测：同裁切下圆内白底 2.4% / 边缘带 12.6%。
 *   ③ **`alt=""`（装饰性）** —— 头像不承载任何新信息：身份由紧邻的 `h1` 与定位陈述
 *      承担。⛔ 这不是「对承载信息的可见内容用 aria-hidden」（那条是禁止的），
 *      而是「装饰性图片」的正当用法；axe 的 `image-alt` 亦以空 alt 通过。
 *   ⚠ 素材本身**无署名义务、不具身份标记作用**（用户 2026-10-11 裁决：开源形象＋AIGC，
 *     非商用、仅为个性化展示）⇒ 不进页脚 `footer__credits`，全站匿名约定不受影响。
 */
export function Hero({ displayName, tagline, hasFeatured = false }: HeroProps) {
  return (
    <section id="top" className="hero">
      <HeroPositionMap />
      <div className="container hero__inner">
        {/* 身份簇：头像 ＋ 定位陈述/名字/标语（★ 纪律①：头像在左侧） */}
        <div className="hero__lead">
          {/* ⚠ `srcSet` 的档位与 CSS 的 `--hero-avatar-w` 及本处 `sizes` **三处同值**：
              桌面 112（2x 取 224）、<1024px 降到 84（彼时仍取 224，因 168 档被裁掉了 ——
              84@2x=168 < 224，浏览器取最近的更大档）。⛔ 改尺寸须三处同改。 */}
          <img
            className="hero__avatar"
            src="/avatar/avatar-112.webp"
            srcSet="/avatar/avatar-112.webp 112w, /avatar/avatar-224.webp 224w"
            sizes="(min-width: 1024px) 112px, 84px"
            width={112}
            height={112}
            alt=""
            decoding="async"
          />
          <div className="hero__lead-text">
            <p className="hero__eyebrow" data-spotlight="micro">{PROFILE_ROLE}</p>
            <h1 className="hero__title">{displayName}</h1>
            <p className="hero__tagline prose">{tagline}</p>
          </div>
        </div>
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
