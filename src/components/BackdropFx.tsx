'use client';

/**
 * 背景特效宿主（客户端边界 + 熔断 + 懒加载）。
 *
 * ★ 四件事，缺一不可：
 *   1. **客户端边界**：`@tsparticles/react` 的发布包**没有** `'use client'`，
 *      直接引入会被当成服务端组件。故这里自包一层并把重物交给 `dynamic`。
 *   2. **懒加载**：`next/dynamic({ ssr: false })` ⇒ 引擎代码不进首屏 JS
 *      （实测：`/` 首屏仍 106 kB，粒子独立分块 105 KB / gzip 30 KB）。
 *   3. **熔断（动效）**：系统 `prefers-reduced-motion: reduce` 或动效开关 `off`
 *      ⇒ **卸载画布**（省 CPU/电量，也符合前庭敏感用户的预期）。
 *   4. **熔断（主题）**：只在**夜间**挂载。浅色下画布已被 CSS `display:none` 隐藏，
 *      但「隐藏 ≠ 不运行」—— 挂着的 rAF 仍在算 ⇒ 必须**卸载**。
 *
 * ★ 为什么同时看 `data-motion` 属性与 `localStorage`：
 *   动效开关的写入顺序是「先落属性、后写存储」，只看存储会拿到**上一拍**的值
 *   （实测：只看存储时运行中关动静默失效）。属性是 CSS 的真相源，也是这里的主判据。
 *
 * ★ 退化路径：熔断/浅色 ⇒「没有粒子」，背景照片仍在（⛔ 不是「没有背景」）。
 */
import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

import { MOTION_STORAGE_KEY } from '@/lib/motion';

const StarfieldCanvas = dynamic(() => import('./backdrop/StarfieldCanvas'), {
  ssr: false,
  loading: () => null,
});

/** 当前是否处于「夜间」（强制档优先于系统档，与 CSS 的三态选择器同口径）。 */
function isNightTheme(): boolean {
  const attr = document.documentElement.getAttribute('data-theme');
  if (attr === 'dark') return true;
  if (attr === 'light') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function motionAllowed(): boolean {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  // 属性优先（CSS 真相源）；存储仅作二次兜底
  if (document.documentElement.getAttribute('data-motion') === 'off') return false;
  try {
    if (localStorage.getItem(MOTION_STORAGE_KEY) === 'off') return false;
  } catch {
    /* 隐私模式：按「允许」处理，交给上面的媒体查询兜底 */
  }
  return true;
}

export function BackdropFx() {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const sync = () => setEnabled(isNightTheme() && motionAllowed());
    sync();

    const motionMq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const schemeMq = window.matchMedia('(prefers-color-scheme: dark)');
    motionMq.addEventListener('change', sync);
    schemeMq.addEventListener('change', sync);

    const observer = new MutationObserver(sync);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme', 'data-motion'],
    });

    return () => {
      motionMq.removeEventListener('change', sync);
      schemeMq.removeEventListener('change', sync);
      observer.disconnect();
    };
  }, []);

  if (!enabled) return null;

  return (
    <span className="backdrop__fx">
      <StarfieldCanvas />
    </span>
  );
}
