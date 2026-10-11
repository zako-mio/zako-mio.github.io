'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  MOTION_LABELS,
  MOTION_MODES,
  MOTION_STORAGE_KEY,
  motionForcesOn,
  motionForcesOff,
  type MotionMode,
} from '@/lib/motion';

const NEXT_MODE: Record<MotionMode, MotionMode> = {
  system: 'on',
  on: 'off',
  off: 'system',
};

/**
 * 三态落属性（★ 批十：**必须三态各不相同**）。
 *   off    ⇒ `data-motion="off"`（CSS 与 JS 双熔断）
 *   on     ⇒ `data-motion="on"` （**覆盖 OS 的 reduce** —— 用户显式要求）
 *   system ⇒ 不落属性（交给 CSS 的 `prefers-reduced-motion` 裁决）
 * ⛔ 早先版本 `on` 与 `system` 都只是 removeAttribute ⇒ 两者不可区分，
 *   于是「动效开」在 OS 开了 reduce 的机器上被静默压掉（实测踩到）。
 */
function applyMode(mode: MotionMode) {
  const root = document.documentElement;
  if (motionForcesOff(mode)) root.setAttribute('data-motion', 'off');
  else if (motionForcesOn(mode)) root.setAttribute('data-motion', 'on');
  else root.removeAttribute('data-motion');
}

/**
 * 动效三态切换（跟随系统 / 动效开 / 动效关）。
 *
 * ★ 与 ThemeToggle 同构（同一套「系统 → 开 → 关」循环先例），理由：
 *   站点已有三态主题的交互契约与留痕，动效开关沿用它 ⇒ 用户不必学第二套。
 * ★ 「跟随系统」＝不落任何属性，由 CSS 的 `prefers-reduced-motion` 裁决；
 *   ⛔ 切换只改属性，不接管 CSS 真相源。
 * ★ 批20.5（F2 修复）：可选 `kindLabel` ＝ 可见文本的**类型前缀**（见 `ThemeToggle` 同名参数）。
 *   本件目前只在左栏使用，与主题开关相邻 ⇒ 默认缺省时也不产生歧义，但为两件同构仍按参数走。
 */
export function MotionToggle({ kindLabel }: { kindLabel?: string } = {}) {
  const [mode, setMode] = useState<MotionMode>('system');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    let initial: MotionMode = 'system';
    try {
      const stored = localStorage.getItem(MOTION_STORAGE_KEY);
      if (stored === 'off' || stored === 'on') initial = stored;
    } catch {
      initial = 'system';
    }
    setMode(initial);
    setMounted(true);
  }, []);

  const toggle = useCallback(() => {
    setMode((current) => {
      const next = NEXT_MODE[current];
      applyMode(next);
      try {
        if (next === 'system') localStorage.removeItem(MOTION_STORAGE_KEY);
        else localStorage.setItem(MOTION_STORAGE_KEY, next);
      } catch {
        /* 隐私模式下 localStorage 不可用：本轮内属性已生效，不阻塞 */
      }
      return next;
    });
  }, []);

  const label = MOTION_LABELS[mode];

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={`动效：${label}。点击切到${MOTION_LABELS[NEXT_MODE[mode]]}`}
      title={`动效：${label}`}
    >
      <span aria-hidden="true" className="theme-toggle__dot theme-toggle__dot--motion" />
      <span className="theme-toggle__text" suppressHydrationWarning>
        {mounted ? (kindLabel ? `${kindLabel}：${label}` : label) : (kindLabel ?? '动效')}
      </span>
    </button>
  );
}

export const MOTION_MODE_COUNT = MOTION_MODES.length;
