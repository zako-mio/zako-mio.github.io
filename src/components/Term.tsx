import type { ReactNode } from 'react';

import { glossaryEntry } from '@/lib/glossary';

export interface TermProps {
  /** `src/data/glossary.json` 里的 `id`（或任何已登记别名）。⛔ 取不到即构建期抛错。 */
  id: string;
  /** 显示文本；缺省用词条本身的 `term`。 */
  children?: ReactNode;
  /**
   * 附加到**触发器** `<button>` 上的类名（批十五 W2-①）。
   * ★ 用途＝**保持接线前的既有外观**（如可采集性徽标的 `badge badge--level`、
   *   缺失值的 `mtable__na`）——接线只换语义通道（`title` → 解释层），⛔ 不改观感。
   */
  className?: string;
}

/**
 * 术语解释层（第十四批 W2）。
 *
 * ★ **单一真相源**：解释文字只从 `src/data/glossary.json` 取（经 `src/lib/glossary.ts`），
 *   ⛔ 组件里不得另写一句解释 —— 那正是本能力要消灭的「第二处解释」。
 *
 * ★ **为什么触发器是 `<button>` 而不是 `<span>`**：
 *   ① 键盘可达（原生可聚焦，⛔ 不靠 `tabindex` 抄近路）；
 *   ② 触屏**点按即聚焦** ⇒ 无 JS 也能展开（`:focus-within`，见 CSS）；
 *   ③ 本站判据「悬停反馈面 ≡ 点击热区」要求**真实可点目标自身有 hover 反馈**
 *      （`surface_hit_probe` 的反向检查）——用 `<span>` 会直接被判「无自身反馈」。
 *   外观仍是行内文字（CSS 里 `appearance/background/border` 全部复位）。
 *
 * ★ **无 JS 可读（渐进增强）**：定义面板**常驻 DOM**（服务端渲染），
 *   呈现由 CSS 的 `:hover` / `:focus-within` 承担 ⇒ 禁用 JS 时键盘与触屏仍可读。
 *   JS 只补一件事：`Esc` 关闭（见 `MotionRuntime`）。⛔ 不把内容交给 JS 注入。
 *
 * ★ 语义：面板 `role="tooltip"`，触发器用 `aria-describedby` 关联。
 *   ⚠ 面板默认 `display:none`，但 `aria-describedby` 对**被直接引用**的隐藏节点仍参与
 *     可访问名称/描述计算 ⇒ 读屏依旧能念出解释（ARIA accname 规范行为）。
 */
export function Term({ id, children, className }: TermProps) {
  const entry = glossaryEntry(id);
  const tipId = `glossary-${entry.id}`;
  const triggerClass = className ? `term__trigger ${className}` : 'term__trigger';
  return (
    <span className="term">
      <button type="button" className={triggerClass} aria-describedby={tipId}>
        {children ?? entry.term}
      </button>
      <span className="term__def" id={tipId} role="tooltip">
        <span className="term__name">{entry.term}</span>
        <span className="term__body">{entry.definition}</span>
        <span className="term__boundary">{entry.boundary}</span>
      </span>
    </span>
  );
}
