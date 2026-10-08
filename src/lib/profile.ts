/**
 * 画像数据（匿名）—— 单一真相源。
 *
 * 本文件原先只有三组标签 + 一句 lead（上一版走查判为「展示自己的信息偏少」）。
 * 第五批在此**加厚**为分层结构，并按「落点唯一」分发给各呈现面：
 *   · `PROFILE_ROLE` / `PROFILE_FOCUS`  → 左栏 masthead（站点级标识，四处复用）
 *   · `PROFILE_LEAD` / `PROFILE_PRACTICE` → `/about` 技术画像与工作方式
 *   · `PROFILE_WORKING_ON`              → `/about` 「近期在做」
 *   · `PROFILE_TIMELINE`                → `/about` 时间线
 *   · `PROFILE_TOOLKIT`                 → `/about` 工具链
 * ⛔ 数字（项目数、指标）一律不放这里 —— 唯一落点是 `/stats`，
 *   本文件只承载**人工声明的画像**，不承载任何聚合读数。
 *
 * ⛔ 完全匿名约束：不得出现姓名、学校、单位、地域、可反查账号等可实名定位字段；
 *    年份只到「年」，不写月份与具体日期，避免可反查。
 */

export interface ProfileGroup {
  key: string;
  label: string;
  items: string[];
}

export interface ProfileTimelineEntry {
  /** 只到年份，⛔ 不写月份/日期（可反查风险） */
  year: string;
  title: string;
  note: string;
}

/** 一句话定位：Hero、左栏、`/about` 顶部共用。⛔ 不写数字。 */
export const PROFILE_ROLE = '数据科学 × AI Agent 工程';

/** 关注方向：左栏 masthead 的紧凑标签组（站点级标识，非 `/about` 专属区块）。 */
export const PROFILE_FOCUS = ['AI Agent 工程', '机器学习建模', '运筹优化', '可视化叙事'];

export const PROFILE_GROUPS: ProfileGroup[] = [
  {
    key: 'background',
    label: '背景',
    items: ['开源实践主线：独立完成 opencode 自进化 Agent 体系改造', '业务×技术复合：数据科学 × 电商管理'],
  },
  {
    key: 'directions',
    label: '技术方向',
    items: ['AI Agent 工程', '机器学习建模', '运筹优化'],
  },
  {
    key: 'interests',
    label: '兴趣',
    items: ['技术自驱', '工具链折腾', '体系化复盘', '可视化叙事', '开源分享'],
  },
];

export const PROFILE_LEAD =
  '以「开源实践」为主线，把业务问题翻译成数据与算法问题，再用可复现的工程体系交付结论。';

/** 「近期在做」：三条进行中的主线，给出**具体动作**而非口号。 */
export const PROFILE_WORKING_ON: string[] = [
  '把「口径先定、数字后采」固化成可机检的判据，让结论没法悄悄漂移。',
  '给知识图谱类作品补结构复算：不采信自述的层数，用构建期 headless 复跑对账。',
  '把网站本身当作一件作品来打磨——可读性由图形与结构承担，而不是靠标点和换行。',
];

/** 工作方式：原先是 `/about` 组件里的字面数组，现外置到数据件（便于跨页复用与校订）。 */
export const PROFILE_PRACTICE: string[] = [
  '单一真相源 + 派生：能派生的数字不手抄，改了源就重生成。',
  '可复现优先：结论要能回源，取证件与门控随产物一起留档。',
  '先定口径再采数：术语不一致时先写规范，宁可空着也不拼凑可比性。',
  '原型先于讨论：聊不拢的地方就出一个能跑的样张。',
];

/** 工具链：只列真实用到的，且与技术方向分层（⛔ 不堆砌）。 */
export const PROFILE_TOOLKIT: ProfileGroup[] = [
  {
    key: 'lang',
    label: '语言',
    items: ['Python', 'TypeScript', 'SQL'],
  },
  {
    key: 'build',
    label: '构建与前端',
    items: ['Next.js', 'React', 'Node', '静态导出'],
  },
  {
    key: 'viz',
    label: '可视化与图谱',
    items: ['ECharts', 'Cytoscape.js', 'D3', 'SVG'],
  },
  {
    key: 'ops',
    label: '工程与交付',
    items: ['Git / GitHub Actions', '门控与负向夹具', '可复现留档'],
  },
];

/** 时间线：⛔ 年份级粒度；条目讲「做了什么」，不讲「在哪做的」。 */
export const PROFILE_TIMELINE: ProfileTimelineEntry[] = [
  {
    year: '2026',
    title: 'Agent 工程体系化',
    note: '把自进化 Agent 的改造过程沉淀为可复现的体系：门控、留档、复盘三件套。',
  },
  {
    year: '2025',
    title: '知识图谱与方法论交付',
    note: '多套 DAG 组织的方法论知识图谱，双交付（交互图 + AI 友好 MD）。',
  },
  {
    year: '2024',
    title: '数据与算法落地',
    note: '在业务场景里做端到端决策：问题定义、建模、验证到结论交付。',
  },
  {
    year: '2023',
    title: '复合背景成形',
    note: '电商管理与数据科学两线并行，形成「业务 × 技术」的翻译式工作法。',
  },
];
