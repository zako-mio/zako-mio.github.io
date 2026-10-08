import type { Metadata } from 'next';

import { SiteFooter } from '@/components/SiteFooter';
import { SiteNav } from '@/components/SiteNav';
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const { generatedAt } = loadCatalog();
  const runId = process.env.NEXT_PUBLIC_RUN_ID ?? null;

  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <ThemeScript />
        <meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)" />
        <meta name="theme-color" content="#0B1220" media="(prefers-color-scheme: dark)" />
      </head>
      <body>
        <a className="skip-link" href="#main">
          跳到主要内容
        </a>
        <SiteNav />
        <main id="main">{children}</main>
        <SiteFooter displayName={siteConfig.display_name} generatedAt={generatedAt} runId={runId} />
      </body>
    </html>
  );
}
