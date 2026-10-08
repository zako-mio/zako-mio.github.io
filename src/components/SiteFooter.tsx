import Link from 'next/link';

export interface SiteFooterProps {
  displayName: string;
  generatedAt?: string | null;
  runId?: string | null;
}

const SITEMAP = [
  { href: '/', label: '首页' },
  { href: '/works', label: '作品' },
  { href: '/stats', label: '聚合' },
  { href: '/about', label: '关于' },
];

export function SiteFooter({ displayName, generatedAt = null, runId = null }: SiteFooterProps) {
  const year = new Date().getFullYear();
  const github = 'https://github.com/zako-mio';

  return (
    <footer className="footer">
      <div className="container footer__inner">
        <div className="footer__top">
          <nav className="footer__sitemap" aria-label="站点地图">
            {SITEMAP.map((item) => (
              <Link className="footer__link" href={item.href} key={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
          <a className="footer__top-link" href="#top">
            回到顶部 ↑
          </a>
        </div>
        <p className="footer__copy">
          © {year} {displayName} · 内容以各项目仓库为准 ·{' '}
          <a href={github} rel="noopener noreferrer" target="_blank">
            GitHub
          </a>
        </p>
        <p className="footer__meta">
          {generatedAt ? <span>数据更新：{generatedAt}</span> : null}
          {runId ? <span> · build {runId}</span> : null}
          <span>
            {' '}
            · 静态导出（Next.js{' '}
            <code>output: &apos;export&apos;</code>）
          </span>
        </p>
      </div>
    </footer>
  );
}
