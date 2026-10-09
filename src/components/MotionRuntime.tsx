'use client';

import { useEffect } from 'react';

import { MOTION_RUNTIME_FLAG } from '@/lib/motion';

/**
 * 动效运行时（全站唯一一处 IntersectionObserver）。
 *
 * ★ 为什么是一个「无渲染」的全局件，而不是给每张卡片包一层客户端组件：
 *   后者会把每个区块都拖进客户端包体。本件只占一个极小的 client chunk，
 *   一次 observer 覆盖全站所有 `[data-reveal]` ⇒ 省包体、行为也一致。
 *
 * ★ 为什么**不**在这里判断 reduced-motion / data-motion：
 *   那两条熔断由 CSS 单独承担（`opacity:1 !important`）。若此处再判一次并提前
 *   return，则用户**运行中把动效打开**时，未进视口的元素会永远停在隐藏态。
 *   让 CSS 做唯一裁决、本件只负责「打上 .is-in」，两条路径就不会打架。
 *
 * ★ 落 `data-motion-ready` 标志：告诉 pre-paint 脚本里的兜底定时器
 *   「运行时已接管」，避免它 1.8s 后把所有元素一次性摊平。
 */
export function MotionRuntime() {
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute(MOTION_RUNTIME_FLAG, '');

    // ---------------------------------------------------------------- 指针位置
    // ★ 第八批（裁决④ · T1）：把指针的**视口坐标**喂给 `.backdrop__glow`（背景光斑）。
    //   门槛（与卡片光斑同口径）：精确指针 + 动效未被熔断。
    //   ⛔ 不新增监听器：与卡片光斑共用下面这**同一个**委托 listener。
    //   ⛔ 变量写在光斑元素**自身**上（不是 :root）：改 :root 的自定义属性会让整棵树重算样式，
    //      而写在元素上只影响它自己。光斑靠 transform 移动 ⇒ 合成层，不触发重绘。
    const finePointer = window.matchMedia('(pointer: fine)').matches;
    const coarsePointer = window.matchMedia('(pointer: coarse)').matches;
    const motionOff = root.getAttribute('data-motion') === 'off';
    // ★ 批十：「动效开」＝用户显式要求 ⇒ 忽略 OS 的 reduce（与 CSS 的 :not([data-motion='on']) 同口径）。
    const motionForcedOn = root.getAttribute('data-motion') === 'on';
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches && !motionForcedOn;
    // 唯一的「动效可用」口径：⛔ 不要在多处各写一份判定（批十教训 b95：漏一处＝半修状态）。
    const motionAllowed = !motionOff && !reduced;

    let onPointerMove: ((event: PointerEvent) => void) | null = null;
    let onTouchPoint: ((event: TouchEvent) => void) | null = null;
    let onTouchEnd: (() => void) | null = null;

    function removeListeners() {
      if (onPointerMove) window.removeEventListener('pointermove', onPointerMove);
      if (onTouchPoint) {
        window.removeEventListener('touchstart', onTouchPoint);
        window.removeEventListener('touchmove', onTouchPoint);
      }
      if (onTouchEnd) {
        window.removeEventListener('touchend', onTouchEnd);
        window.removeEventListener('touchcancel', onTouchEnd);
      }
    }

    // ── 精确指针（桌面）：光斑跟随鼠标 ＋ 卡片光斑（--mx/--my）。
    if (finePointer && motionAllowed) {
      const glow = document.querySelector<HTMLElement>('.backdrop__glow');
      let pointerFlagged = false;
      let current: HTMLElement | null = null;
      onPointerMove = (event: PointerEvent) => {
        if (glow) {
          glow.style.setProperty('--pointer-x', `${event.clientX}px`);
          glow.style.setProperty('--pointer-y', `${event.clientY}px`);
          if (!pointerFlagged) {
            pointerFlagged = true;
            root.setAttribute('data-pointer', '');
          }
        }
        const target = event.target as Element | null;
        const card = target?.closest?.('.card') as HTMLElement | null;
        if (card !== current) current = card;
        if (!card) return;
        const rect = card.getBoundingClientRect();
        card.style.setProperty('--mx', `${event.clientX - rect.left}px`);
        card.style.setProperty('--my', `${event.clientY - rect.top}px`);
      };
      window.addEventListener('pointermove', onPointerMove, { passive: true });
    }

    // ── 触屏（★ 批十一 F-d1）：**合成层柔光斑**替代已关闭的星野 `grab`。
    //   背景：批十为消除手机卡顿把星野 `onHover.enable` 关到精确指针档，触屏于是没有触摸反馈。
    //   用户裁决：换成**合成层**动画（⛔ 不回 canvas 重绘）。
    //   ⛔ 卡片光斑（--mx/--my）只在上面「精确指针」路径处理 —— 触屏上 `:hover` 本就不适用。
    //   ⚠ 本机 CDP 触摸**不产生 `pointermove`**（只 1 次）⇒ 必须**同时**绑 `touchmove`，否则本机测不到。
    //   ⛔ 全程 `passive: true`：只读坐标、绝不 `preventDefault()` ⇒ 不阻断滚动。
    if ((finePointer || coarsePointer) && motionAllowed) {
      const glow = document.querySelector<HTMLElement>('.backdrop__glow');
      let touchFlagged = false;
      const writePoint = (event: TouchEvent) => {
        const touch = event.touches[0] ?? event.changedTouches[0];
        if (!glow || !touch) return;
        glow.style.setProperty('--pointer-x', `${touch.clientX}px`);
        glow.style.setProperty('--pointer-y', `${touch.clientY}px`);
        if (!touchFlagged) {
          touchFlagged = true;
          root.setAttribute('data-pointer', '');
        }
      };
      onTouchPoint = writePoint;
      // `touchend`/`touchcancel` ⇒ 移除 `data-pointer`，借 `transition: opacity` 淡出（不改位置，就地淡出）。
      onTouchEnd = () => {
        if (!touchFlagged) return;
        touchFlagged = false;
        root.removeAttribute('data-pointer');
      };
      window.addEventListener('touchstart', onTouchPoint, { passive: true });
      window.addEventListener('touchmove', onTouchPoint, { passive: true });
      window.addEventListener('touchend', onTouchEnd, { passive: true });
      window.addEventListener('touchcancel', onTouchEnd, { passive: true });
    }

    // ⚠ 指针/触摸监听必须**先于**下面这个 early return 注册：`/stats` 等页可能没有
    //   `[data-reveal]` 元素，若在后面注册，那些页的指针通道会静默消失。
    const nodes = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal]'));
    if (nodes.length === 0) {
      return removeListeners;
    }

    if (!('IntersectionObserver' in window)) {
      nodes.forEach((node) => node.classList.add('is-in'));
      return removeListeners;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-in');
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: '0px 0px -10% 0px', threshold: 0.06 },
    );

    nodes.forEach((node) => observer.observe(node));

    return () => {
      observer.disconnect();
      removeListeners();
    };
  }, []);

  return null;
}
