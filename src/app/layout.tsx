import type { Metadata } from 'next';

import { Backdrop } from '@/components/Backdrop';
import { MotionRuntime } from '@/components/MotionRuntime';
import { MotionScript } from '@/components/MotionScript';
import { SiteFooter } from '@/components/SiteFooter';
import { SiteNav } from '@/components/SiteNav';
import { SiteRail } from '@/components/SiteRail';
import { ThemeScript } from '@/components/ThemeScript';
import { loadCatalog } from '@/lib/catalog';
import { loadSiteConfig, SITE_ORIGIN, SITE_TAGLINE } from '@/lib/site';

import './globals.css';

const siteConfig = loadSiteConfig();

export const metadata: Metadata = {
  metadataBase: new URL(SITE_ORIGIN),
  title: {
    default: `${siteConfig.site_title} · 技术知识中枢`,
    template: `%s · ${siteConfig.display_name}`,
  },
  description: SITE_TAGLINE,
  alternates: { canonical: '/' },
  icons: { icon: '/favicon.svg' },
  openGraph: {
    type: 'website',
    siteName: siteConfig.site_title,
    title: `${siteConfig.site_title} · 技术知识中枢`,
    description: SITE_TAGLINE,
    url: SITE_ORIGIN,
  },
  twitter: { card: 'summary' },
};

/**
 * 根布局（第五批：加入背景层与左栏外壳）。
 *
 * ★ 结构：`Backdrop`（固定定位、`z-index:-1`、`aria-hidden`）
 *   → `SiteNav`（<1180px 可见）
 *   → `.shell`（≥1180px 两列：左栏 + 内容）
 *   → `MotionRuntime`（无渲染的 IntersectionObserver 宿主）。
 *
 * ★ 为什么导航只留一处可交互实例：左栏与顶部导航承载同一组四路由，
 *   两者同时可见即「同一批入口在首屏出现两遍」——这正是第三批走查修掉的毛病。
 *   故用 CSS 断点二选一，⛔ 不是简单叠加。
 *
 * ★ `theme-color` 两条 meta 与 `--surface-page` 的浅/深取值必须同步：
 *   它们决定移动端浏览器 UI 的配色，属**同一事实的两处书写**，
 *   改令牌时须一并改（本批已同步为 `#f4f7fc` / `#060a14`）。
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  const { generatedAt } = loadCatalog();
  const runId = process.env.NEXT_PUBLIC_RUN_ID ?? null;
  const github = `https://github.com/${siteConfig.owner}`;

  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <ThemeScript />
        <MotionScript />
        <meta name="theme-color" content="#f4f7fc" media="(prefers-color-scheme: light)" />
        <meta name="theme-color" content="#060a14" media="(prefers-color-scheme: dark)" />
      </head>
      <body>
        <a className="skip-link" href="#main">
          跳到主要内容
        </a>
        <Backdrop />
        <SiteNav />
        <div className="shell">
          <div className="shell__rail">
            <SiteRail displayName={siteConfig.display_name} github={github} />
          </div>
          <div className="shell__content">
            <main id="main">{children}</main>
            <SiteFooter
              displayName={siteConfig.display_name}
              generatedAt={generatedAt}
              runId={runId}
            />
          </div>
        </div>
        <MotionRuntime />
      </body>
    </html>
  );
}
