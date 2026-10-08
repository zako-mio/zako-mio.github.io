'use client';

import { useEffect, useState } from 'react';

export interface TocItem {
  id: string;
  label: string;
}

/**
 * 长页目录侧栏（长页可读性）。
 *
 * ★ 只有当前页正文确实分段（≥2 项）时才由调用方渲染；否则不渲染空目录。
 * ★ 滚动高亮沿用既有手写 IntersectionObserver 先例（原 Nav.astro 的 scroll-spy）。
 * ★ no-JS 降级：目录是纯锚点链接，无 JS 时仍可点击跳转，仅高亮不生效。
 */
export function TocSidebar({ items }: { items: TocItem[] }) {
  const [activeId, setActiveId] = useState<string>(items[0]?.id ?? '');

  useEffect(() => {
    if (items.length === 0) return;
    const sections = items
      .map((item) => document.getElementById(item.id))
      .filter((element): element is HTMLElement => element !== null);

    if (sections.length === 0 || !('IntersectionObserver' in window)) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      { rootMargin: '-20% 0px -65% 0px', threshold: [0, 0.2, 0.5, 1] },
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [items]);

  if (items.length === 0) return null;

  return (
    <nav className="toc" aria-label="本页目录">
      <p className="toc__title">本页目录</p>
      <ul className="toc__list">
        {items.map((item) => (
          <li key={item.id}>
            <a
              className="toc__link"
              href={`#${item.id}`}
              aria-current={activeId === item.id ? 'location' : undefined}
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
