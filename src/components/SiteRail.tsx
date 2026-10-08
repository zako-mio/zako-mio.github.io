'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { BrandMark } from './BrandMark';
import { MotionToggle } from './MotionToggle';
import { ThemeToggle } from './ThemeToggle';

import { PROFILE_FOCUS, PROFILE_ROLE } from '@/lib/profile';

/**
 * 左栏常驻导航（第五批新增）。
 *
 * ★ 职责边界（⛔ 不是「第二份导航」，而是宽屏下的**那一份**导航）：
 *   ≥1180px 由本件承担导航、顶部导航整条 `display:none`；
 *   <1180px 本件整条隐藏、顶部导航接管 ⇒ 任意宽度下**可交互的导航有且仅有一处**。
 *
 * ★ IA 纪律（有意的自我约束，`gate_ia_division.py` 的 A10 会机检）：
 *   本件是全站公共件（每页都渲染），因此**不得**携带任何「某页专属」的区块——
 *   ⛔ 不放 `contact__list` / `stats__grid` / `about__grid` / `filterbar`，
 *   ⛔ 不放任何聚合数字（那些的唯一落点是 `/stats`），
 *   ⛔ 不放 `/works/<name>` 详情链接（否则首页枚举数会被公共件抬高）。
 *   它只承载：站点标识（masthead）＋ 四路由导航 ＋ 关注方向 ＋ 两枚开关 ＋ 外链。
 */
interface RailIconProps {
  path: string;
}

/** 内联图标：16px 网格、stroke 1.6、无填充 ⇒ 跟随 `currentColor`，随主题走。 */
function RailIcon({ path }: RailIconProps) {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

const NAV_ITEMS = [
  { href: '/', label: '首页', icon: 'M4 11.5 12 4l8 7.5M6 10.5V20h12v-9.5' },
  { href: '/works', label: '作品', icon: 'M4 5h7v7H4zM13 5h7v7h-7zM4 14h7v5H4zM13 14h7v5h-7z' },
  { href: '/stats', label: '聚合', icon: 'M4 19V9M10 19V5M16 19v-7M22 19H2' },
  { href: '/about', label: '关于', icon: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 8.5v.01M11 12h1v5h1' },
];

function isActive(pathname: string, href: string) {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

export interface SiteRailProps {
  displayName: string;
  github: string;
}

export function SiteRail({ displayName, github }: SiteRailProps) {
  const pathname = usePathname() ?? '/';

  return (
    <aside className="rail" aria-label="站点侧栏">
      <Link className="rail__masthead" href="/">
        <BrandMark className="rail__mark" size={38} />
        <span className="rail__names">
          <span className="rail__name">{displayName}</span>
          <span className="rail__role">{PROFILE_ROLE}</span>
        </span>
      </Link>

      <div className="rail__section">
        <p className="rail__label">导航</p>
        <nav aria-label="站点主导航">
          <ul className="rail__nav">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  className="rail__link"
                  href={item.href}
                  aria-current={isActive(pathname, item.href) ? 'page' : undefined}
                >
                  <RailIcon path={item.icon} />
                  <span>{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      <div className="rail__section">
        <p className="rail__label">关注方向</p>
        <ul className="rail__glossary">
          {PROFILE_FOCUS.map((item) => (
            <li className="chip" key={item}>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="rail__foot">
        <div className="rail__controls">
          <ThemeToggle />
          <MotionToggle />
        </div>
        <p className="rail__meta">
          <a href={github} rel="noopener noreferrer" target="_blank">
            GitHub
          </a>
        </p>
      </div>
    </aside>
  );
}
