export const MOTION_STORAGE_KEY = 'ui-motion';

export const MOTION_MODES = ['system', 'on', 'off'] as const;

export type MotionMode = (typeof MOTION_MODES)[number];

export const MOTION_LABELS: Record<MotionMode, string> = {
  system: '跟随系统',
  on: '动效开',
  off: '动效关',
};

/** 该模式是否把动效钉死为「关」（只有 off 会写 `data-motion="off"`）。 */
export function motionForcesOff(mode: MotionMode): boolean {
  return mode === 'off';
}

/**
 * 该模式是否把动效钉死为「开」。
 *
 * ★ 批十（用户裁决）：`on` ＝ 用户**显式要求**，必须覆盖 OS 的 `prefers-reduced-motion: reduce`；
 *   而 `system`（＝不落属性）才是「尊重 OS」的那一档。
 *   ⇒ 落 `data-motion="on"` 后，CSS 的 reduce 熔断块（均以 `:not([data-motion='on'])` 限定）
 *     与 JS 侧三处 `motionAllowed()` 都据此放行。
 */
export function motionForcesOn(mode: MotionMode): boolean {
  return mode === 'on';
}

/**
 * 动效初始化脚本（pre-paint，与主题脚本同批注入 <head>）。
 *
 * ★ 它只做两件事，且都必须是**同步、先于首帧**的：
 *   1. 给 <html> 打 `js-motion` —— CSS 里「进场隐藏态」**只在这个类下生效**，
 *      于是 **无 JS 时元素默认可见**（⛔ 不出现「脚本没跑到 = 白屏」）。
 *   2. 读用户偏好：`off` ⇒ 落 `data-motion="off"`；`on` ⇒ 落 `data-motion="on"`
 *      （缺省即 `system`，不落属性，交给 CSS 媒体查询）。
 *      ★ 批十：`on` **必须**也落属性 —— 否则首帧无法与 `system` 区分，
 *        「动效开」在 OS reduce 下会被静默压掉（且 CSS 的 `:not([data-motion='on'])` 拿不到信号）。
 *
 * ★ 兜底（防「脚本没跑到 = 内容永久不可见」）：
 *   `js-motion` 一打上，隐藏态就生效；若随后 **React 水合失败或未及时接管**，
 *   元素会一直停在 opacity:0。故此处挂一个**一次性**定时器：
 *   1.8s 后若 `MotionRuntime` 仍未落 `data-motion-ready`，就把所有
 *   `[data-reveal]` 直接置为终态 —— 退化路径是「没有动画」，⛔ 绝不是「没有内容」。
 */
export const MOTION_INIT_SCRIPT = `(function(){var d=document.documentElement;function revealAll(){var n=d.querySelectorAll('[data-reveal]');for(var i=0;i<n.length;i++){n[i].classList.add('is-in');}}try{d.classList.add('js-motion');var m=localStorage.getItem('${MOTION_STORAGE_KEY}');if(m==='off'){d.setAttribute('data-motion','off');}else if(m==='on'){d.setAttribute('data-motion','on');}}catch(e){d.classList.add('js-motion');}setTimeout(function(){if(!d.hasAttribute('data-motion-ready')){revealAll();}},1800);})();`;

export const MOTION_RUNTIME_FLAG = 'data-motion-ready';
