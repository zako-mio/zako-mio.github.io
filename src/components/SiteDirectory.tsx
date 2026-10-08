import Link from 'next/link';

export interface DirectoryItem {
  href: string;
  label: string;
  question: string;
  note: string;
}

export interface SiteDirectoryProps {
  items: DirectoryItem[];
  github: string;
}

/**
 * 路由图标（第五批：把「分区」从纯文字列表变成可扫读的图形索引）。
 * ⛔ 图标只作**指向性**提示，不承载语义 ⇒ `aria-hidden`，
 *   每个入口的可读语义仍由 `label` / `question` / `note` 三段文字承担。
 */
const ICONS: Record<string, string> = {
  '/works': 'M4 5h7v7H4zM13 5h7v7h-7zM4 14h7v5H4zM13 14h7v5h-7z',
  '/stats': 'M4 19V9M10 19V5M16 19v-7M22 19H2',
  '/about': 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 8.5v.01M11 12h1v5h1',
  github: 'M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9c0-1 .1-1.4-.5-2 2.8-.3 4.5-1.5 4.5-5a3.9 3.9 0 0 0-1.1-2.7 3.6 3.6 0 0 0-.1-2.7s-1.1-.3-3.5 1.3a9.4 9.4 0 0 0-5 0C7.4 4.4 6.3 4.7 6.3 4.7a3.6 3.6 0 0 0-.1 2.7A3.9 3.9 0 0 0 5 10.1c0 3.5 1.7 4.7 4.5 5-.6.6-.6 1.2-.5 2V21',
};

function RouteIcon({ href }: { href: string }) {
  const key = href.startsWith('http') ? 'github' : href;
  const path = ICONS[key];
  if (!path) return null;
  return (
    <svg
      className="directory__icon"
      width="18"
      height="18"
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

/**
 * 站点分区导航（第三批新增，第五批加图形层）。
 *
 * ★ 职能：首页承担「枢纽」——把每个分页**回答什么问题**摆在读者面前，
 *   使「换页」有可预期的信息增量，而不是撞上同一批内容。
 * ★ 判据对齐（`scripts/gate_ia_division.py`）：
 *   - 本区块只放**跨页入口**，⛔ 不复述任何分页的专属区块或数字；
 *   - 数字唯一落点 = `/stats`，画像与联系唯一落点 = `/about`，
 *     全量作品枚举唯一落点 = `/works`；
 *   - ⛔ 不新增色值：图标与序号都走既有令牌（对比度门控读 globals.css）。
 */
export function SiteDirectory({ items, github }: SiteDirectoryProps) {
  const rows = [
    ...items,
    {
      href: github,
      label: 'GitHub',
      question: '源代码仓库',
      note: '全部公开项目与本站自身的提交历史',
    },
  ];

  return (
    <section id="directory" className="section section--tight" data-reveal>
      <div className="container">
        <header className="section__head">
          <h2 className="section__title">站点分区</h2>
          <p className="section__subtitle">每页只回答一个问题 · 从这里直达对应页</p>
        </header>

        <ul className="related__list directory">
          {rows.map((row, index) => {
            const external = row.href.startsWith('http');
            const inner = (
              <>
                <span className="directory__index" aria-hidden="true">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <RouteIcon href={row.href} />
                <span className="directory__label">{row.label}</span>
              </>
            );

            return (
              <li className="related__item directory__item" key={row.href}>
                {external ? (
                  <a className="related__link directory__head" href={row.href} rel="noopener noreferrer" target="_blank">
                    {inner}
                  </a>
                ) : (
                  <Link className="related__link directory__head" href={row.href}>
                    {inner}
                  </Link>
                )}
                <span className="related__shared">
                  {row.question} —— {row.note}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
