export const MOTION_STORAGE_KEY = 'ui-motion';

export const MOTION_MODES = ['system', 'on', 'off'] as const;

export type MotionMode = (typeof MOTION_MODES)[number];

export const MOTION_LABELS: Record<MotionMode, string> = {
  system: '跟随系统',
  on: '动效开',
  off: '动效关',
};

/** 该模式是否把动效钉死为「关」（只有 off 会写属性；system 交给 CSS 媒体查询）。 */
export function motionForcesOff(mode: MotionMode): boolean {
  return mode === 'off';
}

/**
 * 动效初始化脚本（pre-paint，与主题脚本同批注入 <head>）。
 *
 * ★ 它只做两件事，且都必须是**同步、先于首帧**的：
 *   1. 给 <html> 打 `js-motion` —— CSS 里「进场隐藏态」**只在这个类下生效**，
 *      于是 **无 JS 时元素默认可见**（⛔ 不出现「脚本没跑到 = 白屏」）。
 *   2. 读用户偏好，`off` 时落 `data-motion="off"`（全局熔断由 CSS 承担）。
 *
 * ★ 兜底（防「脚本没跑到 = 内容永久不可见」）：
 *   `js-motion` 一打上，隐藏态就生效；若随后 **React 水合失败或未及时接管**，
 *   元素会一直停在 opacity:0。故此处挂一个**一次性**定时器：
 *   1.8s 后若 `MotionRuntime` 仍未落 `data-motion-ready`，就把所有
 *   `[data-reveal]` 直接置为终态 —— 退化路径是「没有动画」，⛔ 绝不是「没有内容」。
 */
export const MOTION_INIT_SCRIPT = `(function(){var d=document.documentElement;function revealAll(){var n=d.querySelectorAll('[data-reveal]');for(var i=0;i<n.length;i++){n[i].classList.add('is-in');}}try{d.classList.add('js-motion');if(localStorage.getItem('${MOTION_STORAGE_KEY}')==='off'){d.setAttribute('data-motion','off');}}catch(e){d.classList.add('js-motion');}setTimeout(function(){if(!d.hasAttribute('data-motion-ready')){revealAll();}},1800);})();`;

export const MOTION_RUNTIME_FLAG = 'data-motion-ready';
