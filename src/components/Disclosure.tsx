import type { ReactNode } from 'react';

export interface DisclosureProps {
  summary: string;
  children: ReactNode;
  defaultOpen?: boolean;
  hint?: string;
}

/**
 * 渐进披露（长页可读性）。
 *
 * ★ 用原生 `<details>/<summary>`：无 JS 可用、键盘可达、屏幕阅读器原生支持。
 * ★ `[hidden]` 之外的默认展开由 `open` 属性控制；⛔ 不引入 JS 折叠状态记忆，
 *   避免把可读性机制变成又一个前端状态。
 */
export function Disclosure({ summary, children, defaultOpen = false, hint }: DisclosureProps) {
  return (
    <details className="disclosure" data-spotlight="soft" open={defaultOpen}>
      <summary className="disclosure__summary">
        <span className="disclosure__title">{summary}</span>
        {hint ? <span className="disclosure__hint">{hint}</span> : null}
      </summary>
      <div className="disclosure__body">{children}</div>
    </details>
  );
}
