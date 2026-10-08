import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { catalogSchema, overridesSchema, type Project } from './schema';

export interface CatalogResult {
  projects: Project[];
  generatedAt: string | null;
  ok: boolean;
  hint: string | null;
}

const DATA_PATH = 'src/data/projects.json';
const OVERRIDES_PATH = 'src/data/overrides.json';

const MISSING_HINT =
  '项目数据尚未生成（src/data/projects.json 缺失或为空）。数据管道首次运行后会自动填充，本页暂以空状态展示。';
const INVALID_HINT =
  '项目数据未通过契约校验，已临时降级为空列表；修复 src/data/projects.json 后重新构建即可恢复。';

function readJson(path: string): unknown | null {
  try {
    const abs = resolve(process.cwd(), path);
    if (!existsSync(abs)) return null;
    const raw = readFileSync(abs, 'utf8');
    if (!raw.trim()) return null;
    return JSON.parse(raw) as unknown;
  } catch {
    return null;
  }
}

/**
 * 展示层覆盖：仅允许 featured / order / section / alias。
 * ⛔ 不得写入语义标签（type/domains）——那是取数侧的第二真相源。
 */
export function applyOverrides(projects: Project[], overridesRaw: unknown): Project[] {
  const parsed = overridesSchema.safeParse(overridesRaw);
  if (!parsed.success) return sortProjects(projects);
  const map = parsed.data.overrides;

  const merged = projects.map((project) => {
    const override = map[project.name];
    if (!override) return project;
    return {
      ...project,
      title: override.alias ?? project.title,
      featured: override.featured ?? project.featured,
      order: override.order ?? project.order,
      section: override.section ?? project.section,
    };
  });

  return sortProjects(merged);
}

/** 确定性排序：主线优先 → order → pushed_at 倒序 → name。 */
export function sortProjects(projects: Project[]): Project[] {
  return [...projects].sort((a, b) => {
    if (Boolean(b.featured) !== Boolean(a.featured)) return b.featured ? 1 : -1;
    const orderA = a.order ?? 0;
    const orderB = b.order ?? 0;
    if (orderA !== orderB) return orderA - orderB;
    const pushedA = a.pushed_at ?? '';
    const pushedB = b.pushed_at ?? '';
    if (pushedA !== pushedB) return pushedB.localeCompare(pushedA);
    return a.name.localeCompare(b.name);
  });
}

export function loadCatalog(): CatalogResult {
  const raw = readJson(DATA_PATH);
  if (raw === null) {
    return { projects: [], generatedAt: null, ok: false, hint: MISSING_HINT };
  }

  const parsed = catalogSchema.safeParse(raw);
  if (!parsed.success) {
    return { projects: [], generatedAt: null, ok: false, hint: INVALID_HINT };
  }

  const projects = applyOverrides(parsed.data.projects, readJson(OVERRIDES_PATH));
  return { projects, generatedAt: parsed.data.generated_at, ok: true, hint: null };
}

export function findProject(name: string): Project | null {
  const { projects } = loadCatalog();
  return projects.find((project) => project.name === name) ?? null;
}

/** 零成本派生指标（仅依赖 projects.json 现成字段，不做任何外部采集）。 */
export interface DerivedStats {
  projectCount: number;
  featuredCount: number;
  typeCounts: Array<{ value: string; count: number }>;
  domainCounts: Array<{ value: string; count: number }>;
  languageCounts: Array<{ value: string; count: number }>;
  starTotal: number;
  latestPush: string | null;
  earliestPush: string | null;
}

export function deriveStats(projects: Project[]): DerivedStats {
  const tally = (values: string[]) => {
    const map = new Map<string, number>();
    for (const value of values) map.set(value, (map.get(value) ?? 0) + 1);
    return [...map.entries()]
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
  };

  const pushes = projects.map((p) => p.pushed_at ?? '').filter(Boolean).sort();

  return {
    projectCount: projects.length,
    featuredCount: projects.filter((p) => p.featured).length,
    typeCounts: tally(projects.map((p) => p.type)),
    domainCounts: tally(projects.flatMap((p) => p.domains)),
    languageCounts: tally(projects.map((p) => p.language ?? '未标注')),
    starTotal: projects.reduce((sum, p) => sum + (p.stars ?? 0), 0),
    latestPush: pushes.length > 0 ? pushes[pushes.length - 1] : null,
    earliestPush: pushes.length > 0 ? pushes[0] : null,
  };
}
