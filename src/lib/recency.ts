import type { Project } from './schema';

/**
 * 「项目新鲜度」共享标尺（第五批）——**纯函数**，⛔ 不做任何取数。
 *
 * ★ 为什么坚持「纯」：卡片组件会被 `WorksExplorer`（客户端组件）引用，
 *   若在它依赖的模块里 import `node:fs`，整个 `node:path` 会被拽进客户端包，
 *   构建直接失败（本轮实测踩到：`UnhandledSchemeError: node:path`）。
 *   ⇒ 取数留在服务端页面，这里只放**可序列化**的计算，
 *     谁渲染卡片，谁负责把算好的范围传下去。
 *
 * ★ 为什么要共享标尺：单张卡片上的日期只是一个孤立事实；
 *   把全部项目放进同一条时间轴，读者才能一眼看出「这条线是不是还在动」。
 */
export interface RecencyRange {
  min: number;
  max: number;
}

/**
 * 由项目集合算出共同时间跨度。
 *
 * ⚠ 本模块**不得** import `./catalog`：那会把 `node:fs`/`node:path` 经由
 *   `ProjectCard` → 客户端组件 `WorksExplorer` 的引用链拽进浏览器包，
 *   构建期直接 `UnhandledSchemeError: node:path`（本轮实测踩到两次）。
 *   ⇒ 这里只保留最小自洽的纯计算，⛔ 不复用取数层的 `deriveStats`。
 *
 * ⚠ 范围退化为单点（max <= min）时返回 null ⇒ 调用方**不画**，
 *   ⛔ 不拿「中点」或 0 冒充一个位置。
 */
export function recencyRangeOf(projects: Project[]): RecencyRange | null {
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;

  for (const project of projects) {
    if (!project.pushed_at) continue;
    const value = Date.parse(project.pushed_at);
    if (!Number.isFinite(value)) continue;
    if (value < min) min = value;
    if (value > max) max = value;
  }

  return Number.isFinite(min) && Number.isFinite(max) && max > min ? { min, max } : null;
}

/** 归一化到 [0,1]；数据缺失或范围退化时返回 null（⛔ 不编造位置）。 */
export function recencyRatioOf(
  pushedAt: string | undefined,
  range: RecencyRange | null,
): number | null {
  if (!range || !pushedAt) return null;
  const value = Date.parse(pushedAt);
  if (!Number.isFinite(value)) return null;
  return Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
}

/** 只取年月，供图的端点标注（⛔ 不展示时分秒，噪声大于信息）。 */
export function shortDate(ms: number): string {
  const date = new Date(ms);
  return `${date.getUTCFullYear()}.${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
}
