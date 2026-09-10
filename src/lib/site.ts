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

export function loadSiteConfig(
  path: string = resolve(process.cwd(), 'site.config.json'),
): SiteConfig {
  try {
    const raw = readFileSync(path, 'utf8');
    const parsed = JSON.parse(raw) as Partial<SiteConfig>;
    return { ...DEFAULTS, ...parsed };
  } catch {
    return DEFAULTS;
  }
}
