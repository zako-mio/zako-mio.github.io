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

    const nodes = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal]'));
    if (nodes.length === 0) return;

    if (!('IntersectionObserver' in window)) {
      nodes.forEach((node) => node.classList.add('is-in'));
      return;
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

    // ---------------------------------------------------------------- 卡片光斑
    // 单个**委托**监听器服务全站卡片（⛔ 不逐卡 addEventListener）。
    // 门槛：指针为精确型 + 动效未被熔断；`--mx/--my` 只喂给 CSS 的 radial-gradient，
    // 因此每帧成本 = 一次样式写入，且只在真正位于卡片内时才写。
    const finePointer = window.matchMedia('(pointer: fine)').matches;
    const motionOff = root.getAttribute('data-motion') === 'off';
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let onPointerMove: ((event: PointerEvent) => void) | null = null;
    if (finePointer && !motionOff && !reduced) {
      let current: HTMLElement | null = null;
      onPointerMove = (event: PointerEvent) => {
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

    return () => {
      observer.disconnect();
      if (onPointerMove) window.removeEventListener('pointermove', onPointerMove);
    };
  }, []);

  return null;
}
