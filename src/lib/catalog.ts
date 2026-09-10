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
    if (!existsSync(path)) return null;
    const raw = readFileSync(path, 'utf8');
    if (!raw.trim()) return null;
    return JSON.parse(raw) as unknown;
  } catch {
    return null;
  }
}

function applyOverrides(projects: Project[], overridesRaw: unknown): Project[] {
  const parsed = overridesSchema.safeParse(overridesRaw);
  if (!parsed.success) return projects;
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

  return merged.sort((a, b) => {
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

export function loadCatalog(
  dataPath: string = DATA_PATH,
  overridesPath: string = OVERRIDES_PATH,
): CatalogResult {
  const raw = readJson(resolve(process.cwd(), dataPath));
  if (raw === null) {
    return { projects: [], generatedAt: null, ok: false, hint: MISSING_HINT };
  }

  const parsed = catalogSchema.safeParse(raw);
  if (!parsed.success) {
    return { projects: [], generatedAt: null, ok: false, hint: INVALID_HINT };
  }

  const overrides = readJson(resolve(process.cwd(), overridesPath));
  const projects = applyOverrides(parsed.data.projects, overrides);
  return { projects, generatedAt: parsed.data.generated_at, ok: true, hint: null };
}
