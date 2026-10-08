import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export interface SiteConfig {
  owner: string;
  display_name: string;
  host: string;
  site_title: string;
  contact_email: string;
  gh_api_base: string;
  exclude_repos: string[];
  require_pages: boolean;
  summary_source: string;
  max_summary_len: number;
}

const DEFAULTS: SiteConfig = {
  owner: 'zako-mio',
  display_name: 'zako-mio',
  host: 'zako-mio.github.io',
  site_title: 'zako-mio · Tech Hub',
  contact_email: '1505788754@qq.com',
  gh_api_base: 'https://api.github.com',
  exclude_repos: ['zako-mio.github.io'],
  require_pages: true,
  summary_source: 'description_first',
  max_summary_len: 140,
};

export function loadSiteConfig(): SiteConfig {
  try {
    const raw = readFileSync(resolve(process.cwd(), 'site.config.json'), 'utf8');
    const parsed = JSON.parse(raw) as Partial<SiteConfig>;
    return { ...DEFAULTS, ...parsed };
  } catch {
    return DEFAULTS;
  }
}

/**
 * 站点定位语。
 * ★ 与「关于」区块的分工：定位语是**一句话**，逐条画像在 src/lib/profile.ts。
 * ⛔ 完全匿名约束：此处不得出现可实名定位的字段。
 */
export const SITE_TAGLINE =
  '电商管理 × 数据科学复合背景，聚焦 AI Agent 工程、机器学习建模与运筹优化；长于在不确定环境中做端到端决策落地。';

export const SITE_ORIGIN = 'https://zako-mio.github.io';
