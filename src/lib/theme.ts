export const THEME_STORAGE_KEY = 'ui-theme';

export const THEME_MODES = ['system', 'light', 'dark'] as const;

export type ThemeMode = (typeof THEME_MODES)[number];

export const THEME_LABELS: Record<ThemeMode, string> = {
  system: '跟随系统',
  light: '浅色',
  dark: '深色',
};

/**
 * 防闪烁初始化脚本（pre-paint，必须在 <head> 内联执行）。
 *
 * ★ 三态语义：
 *   - 无 `data-theme` 属性 = 跟随系统（交给 CSS 的 prefers-color-scheme 分支）
 *   - `data-theme="light"` / `data-theme="dark"` = 强制档
 * ★ 写入的 `color-scheme` 由 CSS 的选择器分支承担（见 globals.css），
 *   此处只落属性，避免 JS 与 CSS 两处各自声明真相源。
 */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem('${THEME_STORAGE_KEY}');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t);}else{document.documentElement.removeAttribute('data-theme');}}catch(e){}})();`;
