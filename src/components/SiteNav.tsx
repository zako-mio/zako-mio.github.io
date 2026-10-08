'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { ThemeToggle } from './ThemeToggle';

const NAV_ITEMS = [
  { href: '/', label: '首页' },
  { href: '/works', label: '作品' },
  { href: '/stats', label: '聚合' },
  { href: '/about', label: '关于' },
];

function isActive(pathname: string, href: string) {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav() {
  const pathname = usePathname() ?? '/';

  return (
    <header className="nav">
      <div className="container nav__inner">
        <Link className="nav__brand" href="/">
          zako-mio
        </Link>
        <div className="nav__right">
          <nav aria-label="主导航">
            <ul className="nav__list">
              {NAV_ITEMS.map((item) => (
                <li key={item.href}>
                  <Link
                    className="nav__link"
                    href={item.href}
                    aria-current={isActive(pathname, item.href) ? 'page' : undefined}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
