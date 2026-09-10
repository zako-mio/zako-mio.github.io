import { z } from 'zod';

export const PROJECT_TYPES = [
  'knowledge-graph',
  'knowledge-base',
  'analysis',
  'tutorial',
  'methodology',
] as const;

export const PROJECT_DOMAINS = [
  'agent-engineering',
  'control-theory',
  'llm',
  'algorithms',
  'software-engineering',
  'github',
] as const;

export const projectTypeSchema = z.enum(PROJECT_TYPES);
export const projectDomainSchema = z.enum(PROJECT_DOMAINS);

export const projectSchema = z.object({
  name: z.string().regex(/^[A-Za-z0-9._-]+$/),
  title: z.string().min(1),
  summary: z.string().min(1).max(200),
  type: projectTypeSchema,
  domains: z.array(projectDomainSchema).min(1),
  language: z.string().nullable().optional(),
  stars: z.number().int().min(0).optional(),
  pushed_at: z.string().optional(),
  entry_url: z.string().url(),
  repo_url: z.string().url(),
  has_pages: z.boolean(),
  featured: z.boolean().optional(),
  order: z.number().int().optional(),
  section: z.string().nullable().optional(),
});

export const overrideSchema = z.object({
  featured: z.boolean().optional(),
  order: z.number().int().optional(),
  section: z.string().nullable().optional(),
  alias: z.string().optional(),
});

export const overridesSchema = z.object({
  schema_version: z.string().optional(),
  overrides: z.record(overrideSchema).default({}),
});

export const catalogSchema = z.object({
  schema_version: z.literal('1.0'),
  generated_at: z.string().min(10),
  projects: z.array(projectSchema),
});

export type Project = z.infer<typeof projectSchema>;
export type ProjectType = z.infer<typeof projectTypeSchema>;
export type ProjectDomain = z.infer<typeof projectDomainSchema>;
export type Catalog = z.infer<typeof catalogSchema>;

export const TYPE_LABELS: Record<ProjectType, string> = {
  'knowledge-graph': '知识图谱',
  'knowledge-base': '知识库',
  analysis: '分析',
  tutorial: '教程',
  methodology: '方法论',
};

export const DOMAIN_LABELS: Record<ProjectDomain, string> = {
  'agent-engineering': 'Agent 工程',
  'control-theory': '控制理论',
  llm: '大模型',
  algorithms: '算法',
  'software-engineering': '软件工程',
  github: 'GitHub',
};
