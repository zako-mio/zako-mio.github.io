/**
 * 画像数据（匿名）。
 *
 * 现状问题（本轮修复）：这三组数组原先硬编码在 Astro 的 About.astro 组件里，
 * 改文案必须改组件代码，且 Hero / 关于 / 统计条三处无法共享。
 * 现外置为数据件，与「单一真相源 + 派生」纪律一致。
 *
 * ⛔ 完全匿名约束：这些字段是**人工声明的画像**，不是客观事实；
 *    不得出现姓名、学校、单位、地域、可反查账号等可实名定位字段。
 */
export interface ProfileGroup {
  key: string;
  label: string;
  items: string[];
}

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
