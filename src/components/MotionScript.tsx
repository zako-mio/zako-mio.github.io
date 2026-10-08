import { MOTION_INIT_SCRIPT } from '@/lib/motion';

/**
 * 动效初始化脚本：与 ThemeScript 同样以原始 inline script 注入 <head>，先于首帧执行。
 * ⛔ 不得改为 useEffect —— 那会在水合后执行，隐藏态早已可见，必然闪一下。
 */
export function MotionScript() {
  return <script dangerouslySetInnerHTML={{ __html: MOTION_INIT_SCRIPT }} />;
}
