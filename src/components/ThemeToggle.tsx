'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { THEME_LABELS, THEME_MODES, THEME_STORAGE_KEY, type ThemeMode } from '@/lib/theme';
import { centerOf, withThemeTransition } from '@/lib/view-transition';

const NEXT_MODE: Record<ThemeMode, ThemeMode> = {
  system: 'light',
  light: 'dark',
  dark: 'system',
};

function applyMode(mode: ThemeMode) {
  const root = document.documentElement;
  if (mode === 'system') {
    root.removeAttribute('data-theme');
  } else {
    root.setAttribute('data-theme', mode);
  }
}

/**
 * 明暗三态切换（跟随系统 / 浅色 / 深色）。
 *
 * 沿用 fe-starter-kit templates/content-a-static 的三态循环先例（系统 → 浅 → 深）。
 * ⛔ 切换只改 `data-theme` 属性；`color-scheme` 由 CSS 分支承担，避免双真相源。
 */
export function ThemeToggle() {
  const [mode, setMode] = useState<ThemeMode>('system');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    let initial: ThemeMode = 'system';
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') initial = stored;
    } catch {
      initial = 'system';
    }
    setMode(initial);
    setMounted(true);
  }, []);

  const buttonRef = useRef<HTMLButtonElement>(null);

  const toggle = useCallback(() => {
    setMode((current) => {
      const next = NEXT_MODE[current];
      // 落属性与落存储必须**同步**在一个回调里 —— View Transitions 要求回调同步完成
      withThemeTransition(() => {
        applyMode(next);
        try {
          if (next === 'system') localStorage.removeItem(THEME_STORAGE_KEY);
          else localStorage.setItem(THEME_STORAGE_KEY, next);
        } catch {
          /* 隐私模式下 localStorage 不可用：本轮内属性已生效，不阻塞 */
        }
      }, centerOf(buttonRef.current));
      return next;
    });
  }, []);

  const label = THEME_LABELS[mode];

  return (
    <button
      ref={buttonRef}
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={`配色主题：${label}。点击切到${THEME_LABELS[NEXT_MODE[mode]]}`}
      title={`配色主题：${label}`}
    >
      <span aria-hidden="true" className="theme-toggle__dot" />
      <span className="theme-toggle__text" suppressHydrationWarning>
        {mounted ? label : '主题'}
      </span>
    </button>
  );
}

export const THEME_MODE_COUNT = THEME_MODES.length;
