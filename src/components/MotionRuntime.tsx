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
    let onTermKeydown: ((event: KeyboardEvent) => void) | null = null;
    let onTermLeave: ((event: PointerEvent) => void) | null = null;

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
      if (onTermKeydown) window.removeEventListener('keydown', onTermKeydown);
      if (onTermLeave) window.removeEventListener('pointerout', onTermLeave);
    }

    // ── 术语解释层（第十四批 W2）：**只补 Esc 关闭**。
    //   hover / focus / 触屏点按的**呈现**全由 CSS 承担（`:hover` 与 `:focus-within`）
    //   ⇒ ⛔ 这里不写「展开」逻辑，否则会与 CSS 形成两条互相打架的裁决路径（批十 b95 的教训）。
    //   WAI-ARIA tooltip 模式：Esc 关闭且焦点退回触发器。落 `data-term-closed` 是为了
    //   **同时**压住 hover 路径（CSS 里该规则排在 `:hover` 之后）；指针离开该词时清除。
    onTermKeydown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      const active = document.activeElement as HTMLElement | null;
      const term = active?.closest?.('.term') as HTMLElement | null;
      if (!term) return;
      term.setAttribute('data-term-closed', '');
      active?.blur();
    };
    onTermLeave = (event: PointerEvent) => {
      const target = event.target as Element | null;
      const term = target?.closest?.('.term') as HTMLElement | null;
      if (term && !term.contains(event.relatedTarget as Node | null)) {
        term.removeAttribute('data-term-closed');
      }
    };
    window.addEventListener('keydown', onTermKeydown);
    window.addEventListener('pointerout', onTermLeave, { passive: true });

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
        // ★ 批十三 W1：作用面从写死的 `.card` 泛化为统一约定 `[data-spotlight]`
        //   （三层阻断的第三层）。**仍是同一个委托 listener**，⛔ 未逐件加监听器。
        //   ⚠ `closest()` 能上溯：SVG 子形状（`<rect>`/`<text>`）作 target 时也能找到 HTML 宿主。
        const spot = target?.closest?.('[data-spotlight]') as HTMLElement | null;
        if (spot !== current) current = spot;
        if (!spot) return;
        const rect = spot.getBoundingClientRect();
        spot.style.setProperty('--mx', `${event.clientX - rect.left}px`);
        spot.style.setProperty('--my', `${event.clientY - rect.top}px`);
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

    // ── 进场接管的**作用面**必须持续跟随 DOM，⛔ 不是「挂载时扫描一次」
    // ★ 第十二批修掉的缺陷（★ 全站八闸五探针**无一**覆盖这个作用面）：
    //   本件挂在**根布局**上 ⇒ App Router 的 layout 跨客户端路由**常驻**，
    //   而 `useEffect(…, [])` 全生命周期只跑一次 ⇒ 首次扫描之后，客户端导航新挂载的
    //   `[data-reveal]` **从未被 observe**，永远停在 `html.js-motion [data-reveal]{opacity:0}`
    //   的隐藏态（1.8s 兜底也不会救 —— 它读的 `data-motion-ready` 早已落过）。
    //   实测（`batch12-evidence/repro_motion_nav.py`，`navigation entries=1` 证明是客户端路由）：
    //     · `/` →（客户端点击）→ `/about`：about 的 8 个 section 全部 `opacity=0 / is-in=false`；
    //     · 再从 `/about` 点回 `/`：首页 `#featured` / `#build-notes` / `#directory` 同样全灭。
    //   ⇒ 用户可见症状即「动效开时，切回首页 / 进关于页 ⇒ 内容消失」。
    //   ⇒ 修法＝**从一次性扫描改为持续接管**：MutationObserver 盯 `body` 子树，
    //     新出现的 `[data-reveal]` 立刻交给**同一个** IntersectionObserver（仍全站唯一一处）。
    //     ⚠ 这同时解除了 `ProjectCard` 头注里「动态重渲染的节点不得带 `data-reveal`」的**根因**
    //       （该限制原本是绕开本缺陷，不是设计意图）；`reveal` 是否 opt-in 仍由卡片自己决定。
    //   ⛔ 只观察 `childList`（**不观察 `attributes`**）：下面会给节点加 `.is-in` 类，
    //     把属性变更纳入观察面会自我触发成死循环。
    //   ⛔ 不要退回「early return when nodes.length === 0」：`/works` 没有 `[data-reveal]`，
    //     一旦提前返回，从 `/works` 导航到 `/` 时仍然没人接管首页节点（这正是原缺陷的一半）。
    // 在管节点集合：防重复 observe，并用于回收「已从小卸载」的节点
    // （⛔ 不回收 ⇒ 每次路由切换都会往 Set 里攒一批游离节点，增长无界）。
    const tracked = new Set<Element>();

    /** 无 `IntersectionObserver` 的退化路径：不观察、直接置终态（退化＝没有动画，⛔ 不是没有内容）。 */
    function revealAll(): void {
      document.querySelectorAll<HTMLElement>('[data-reveal]').forEach((node) => node.classList.add('is-in'));
    }

    if (!('IntersectionObserver' in window)) {
      revealAll();
      if (!('MutationObserver' in window)) return removeListeners;
      // 退化路径同样要**持续接管**，否则客户端路由切换后新内容照样不显示。
      const fallbackMutations = new MutationObserver(revealAll);
      fallbackMutations.observe(document.body, { childList: true, subtree: true });
      return () => {
        fallbackMutations.disconnect();
        removeListeners();
      };
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-in');
          observer.unobserve(entry.target);
          tracked.delete(entry.target);
        });
      },
      { rootMargin: '0px 0px -10% 0px', threshold: 0.06 },
    );

    function collectReveals(): void {
      document.querySelectorAll<HTMLElement>('[data-reveal]').forEach((node) => {
        // 已进终态（`.is-in`）的节点不必再观察；重复 observe 同一节点也无意义。
        if (tracked.has(node) || node.classList.contains('is-in')) return;
        tracked.add(node);
        observer.observe(node);
      });
      tracked.forEach((node) => {
        if (node.isConnected) return;
        observer.unobserve(node);
        tracked.delete(node);
      });
    }

    collectReveals();

    if (!('MutationObserver' in window)) {
      // 极老环境：退回「挂载时扫描一次」（行为 == 修复前，仅用于不会有路由切换的场景）。
      return () => {
        observer.disconnect();
        removeListeners();
      };
    }

    const mutations = new MutationObserver(collectReveals);
    mutations.observe(document.body, { childList: true, subtree: true });

    return () => {
      mutations.disconnect();
      observer.disconnect();
      tracked.clear();
      removeListeners();
    };
  }, []);

  return null;
}
