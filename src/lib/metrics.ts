import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { z } from 'zod';

/**
 * E 枢纽聚合指标的读取层。
 *
 * 真相源：`src/data/metrics.json`（采集器产物，CI 每次重采；本地不在版本库中）
 * 口径规范：`specs/e-metrics-spec.md` v1.0（E1–E6 已裁，留档于任务目录）
 *
 * 展示纪律（与规范一一对应）：
 *   E1 不单值化 -> 一个项目可有多个 figure（各自带 scope），**按行展开**
 *   E2 分列     -> layer_count（图论分层）与 stage_count（教学分期）各自成列
 *   E3 分区     -> 三区各自成表，⛔ 不跨区并比
 *   E5 缺失     -> null 一律渲染 `—`，⛔ 不渲染 0
 */

export const METRIC_SECTIONS = ['dag', 'docs', 'papers', 'unclassified'] as const;
export type MetricSection = (typeof METRIC_SECTIONS)[number];

const figureSchema = z.object({
  scope: z.string(),
  entity_count: z.number().int().nullable().optional(),
  group_count: z.number().int().nullable().optional(),
  relation_count: z.number().int().nullable().optional(),
  layer_count: z.number().int().nullable().optional(),
  stage_count: z.number().int().nullable().optional(),
  unit_note: z.string().nullable().optional(),
  provenance: z.string().optional(),
});

const sourceSchema = z.object({
  url: z.string(),
  fetched_at: z.string().optional(),
  text_sha256: z.string().nullable().optional(),
  excerpt: z.string().nullable().optional(),
});

const entrySchema = z.object({
  name: z.string(),
  title: z.string().nullable().optional(),
  section: z.enum(METRIC_SECTIONS),
  collectability: z.string().optional(),
  status: z.string(),
  figures: z.array(figureSchema).default([]),
  version_self: z.string().nullable().optional(),
  notes: z.array(z.string()).default([]),
  source: sourceSchema,
});

export const metricsSchema = z.object({
  schema_version: z.string().optional(),
  as_of: z.string(),
  site: z.string().optional(),
  project_total: z.number().int(),
  declared_total: z.number().int().optional(),
  projects: z.array(entrySchema),
});

export type MetricFigure = z.infer<typeof figureSchema>;
export type MetricEntry = z.infer<typeof entrySchema>;
export type Metrics = z.infer<typeof metricsSchema>;

export interface MetricsResult {
  metrics: Metrics | null;
  ok: boolean;
  hint: string | null;
}

const DATA_PATH = 'src/data/metrics.json';

const MISSING_HINT =
  'E 指标尚未生成（src/data/metrics.json 缺失或为空）。数据管道首次运行后会自动填充，本区暂以空状态展示。';
const INVALID_HINT =
  'E 指标未通过契约校验，已临时降级为空；修复 src/data/metrics.json 后重新构建即可恢复。';

export const METRIC_COLUMNS = [
  { key: 'entity_count', label: '实体' },
  { key: 'group_count', label: '组' },
  { key: 'relation_count', label: '关系' },
  { key: 'layer_count', label: '拓扑层' },
  { key: 'stage_count', label: '学习阶段' },
] as const;

// ⚠ 列名的**解释文字**（旧字段 `hint`）已移除：它曾以 `title` 属性出现两处，
//   与 `src/data/glossary.json` 构成**第二处解释** ⇒ 按 W2 收敛到 glossary
//   （渲染层用 `<Term id={column.key}>`，见 `ProjectFigure` / `MetricsDashboard`）。

export type MetricColumnKey = (typeof METRIC_COLUMNS)[number]['key'];

export const SECTION_LABELS: Record<MetricSection, string> = {
  dag: 'DAG 图谱区',
  docs: '文档集群区',
  papers: '论文库区',
  unclassified: '未分区',
};

/** E3 分区顺序（⛔ 不跨区并比，故分区顺序只是阅读顺序）。 */
export const SECTION_ORDER: MetricSection[] = ['dag', 'docs', 'papers', 'unclassified'];

export const SECTION_NOTES: Record<MetricSection, string> = {
  dag: '图形态交付：主指标为「实体 / 组 / 关系」，部分项目另有拓扑层。多图项目按 scope 分行并列（E1）。',
  docs: '文档集群形态：主指标为知识点与框架画像数，「关系边」不适用（留空，⛔ 不写 0）。',
  papers: '论文库形态：主指标为论文/关键节点数，图谱类维度不适用。',
  unclassified: '未纳入口径规范的项目：按 E5 显式留空，⛔ 不猜测、不并比。',
};

export function loadMetrics(): MetricsResult {
  const absolute = resolve(process.cwd(), DATA_PATH);
  if (!existsSync(absolute)) return { metrics: null, ok: false, hint: MISSING_HINT };
  let raw: unknown;
  try {
    const text = readFileSync(absolute, 'utf8');
    if (!text.trim()) return { metrics: null, ok: false, hint: MISSING_HINT };
    raw = JSON.parse(text) as unknown;
  } catch {
    return { metrics: null, ok: false, hint: INVALID_HINT };
  }
  const parsed = metricsSchema.safeParse(raw);
  if (!parsed.success) return { metrics: null, ok: false, hint: INVALID_HINT };
  return { metrics: parsed.data, ok: true, hint: null };
}

export function groupBySection(metrics: Metrics): Array<{
  section: MetricSection;
  entries: MetricEntry[];
}> {
  return SECTION_ORDER.map((section) => ({
    section,
    entries: metrics.projects.filter((entry) => entry.section === section),
  })).filter((group) => group.entries.length > 0);
}

// ────────────────────────────── 图表产物 ──────────────────────────────

const chartSchema = z.object({
  key: z.string(),
  title: z.string(),
  note: z.string(),
  width: z.number().int(),
  height: z.number().int(),
  rows: z.array(z.object({ name: z.string(), full: z.string(), value: z.number(), scope: z.string() })),
  svg: z.object({ light: z.string(), dark: z.string() }),
});

const chartsSchema = z.object({
  schema_version: z.string().optional(),
  generator: z.string().optional(),
  capability_keys: z.array(z.string()).optional(),
  source: z.record(z.unknown()).optional(),
  charts: z.array(chartSchema),
});

export type Chart = z.infer<typeof chartSchema>;

const CHARTS_PATH = 'src/data/charts.json';

export function loadCharts(): Chart[] {
  const absolute = resolve(process.cwd(), CHARTS_PATH);
  if (!existsSync(absolute)) return [];
  try {
    const parsed = chartsSchema.safeParse(JSON.parse(readFileSync(absolute, 'utf8')) as unknown);
    return parsed.success ? parsed.data.charts : [];
  } catch {
    return [];
  }
}

// ────────────────────────────── 拓扑实测产物 ──────────────────────────────

const topologySchema = z.object({
  schema_version: z.string().optional(),
  generator: z.string().optional(),
  capability_keys: z.array(z.string()).optional(),
  mode: z.string().optional(),
  source: z.record(z.unknown()).optional(),
  graphs: z.array(
    z.object({
      project: z.string(),
      scope: z.string(),
      asset: z.string(),
      url: z.string(),
      analysis: z.object({
        node_count: z.number().int(),
        edge_count: z.number().int(),
        layer_edge_count: z.number().int().optional(),
        layer_note: z.string().optional(),
        component_count: z.number().int(),
        acyclic: z.boolean(),
        longest_path_layers: z.number().int().nullable(),
        cycle_sample: z.array(z.string()).nullable().optional(),
        top_degree: z.array(z.object({ id: z.string(), degree: z.number().int() })).default([]),
        top_betweenness: z
          .array(z.object({ id: z.string(), score: z.number() }))
          .nullable()
          .optional(),
        betweenness_skipped_ids: z.number().int().optional(),
      }),
      claimed: z.object({
        layer_count: z.number().int().nullable(),
        acyclic: z.boolean().nullable(),
      }),
      agreement: z
        .object({ acyclic: z.boolean().nullable(), layers: z.boolean().nullable() })
        .optional(),
    }),
  ),
});

export type GraphAnalysis = z.infer<typeof topologySchema>['graphs'][number];

const TOPOLOGY_PATH = 'src/data/topology.json';

export function loadTopology(): GraphAnalysis[] {
  const absolute = resolve(process.cwd(), TOPOLOGY_PATH);
  if (!existsSync(absolute)) return [];
  try {
    const parsed = topologySchema.safeParse(JSON.parse(readFileSync(absolute, 'utf8')) as unknown);
    return parsed.success ? parsed.data.graphs : [];
  } catch {
    return [];
  }
}
