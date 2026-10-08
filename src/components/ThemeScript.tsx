import { THEME_INIT_SCRIPT } from '@/lib/theme';

/**
 * 防闪烁脚本：以原始 inline script 注入 <head>，先于首帧执行。
 * ⛔ 不得改为 useEffect —— 那会在水合后执行，必然闪一下。
 */
export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />;
}
