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
 * 站点分区导航（第三批新增）。
 *
 * ★ 职能：首页承担「枢纽」——把每个分页**回答什么问题**摆在读者面前，
 *   使「换页」有可预期的信息增量，而不是撞上同一批内容。
 * ★ 判据对齐（`scripts/gate_ia_division.py`）：
 *   - 本区块只放**跨页入口**，⛔ 不复述任何分页的专属区块或数字；
 *   - 数字唯一落点 = `/stats`，画像与联系唯一落点 = `/about`，
 *     全量作品枚举唯一落点 = `/works`；
 *   - ⛔ 不新增样式/令牌：复用既有 `related__*` 与 `section__*` 类，
 *     避免出现第二处色值真相源（对比度门控读的是 globals.css 的令牌）。
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
    <section id="directory" className="section section--tight">
      <div className="container">
        <header className="section__head">
          <h2 className="section__title">站点分区</h2>
          <p className="section__subtitle">每页只回答一个问题 · 从这里直达对应页</p>
        </header>

        <ul className="related__list">
          {rows.map((row) => {
            const external = row.href.startsWith('http');
            return (
              <li className="related__item" key={row.href}>
                {external ? (
                  <a className="related__link" href={row.href} rel="noopener noreferrer" target="_blank">
                    {row.label}
                  </a>
                ) : (
                  <Link className="related__link" href={row.href}>
                    {row.label}
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
