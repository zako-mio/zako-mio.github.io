import { MOTION_STORAGE_KEY } from './motion';

/**
 * 主题切换的**圆形揭示**过渡（第五批深化，渐进增强）。
 *
 * ★ 为什么用 View Transitions 而不是给每个元素加 `transition: background-color`：
 *   本站背景由**主题分帧**驱动（`.backdrop__photo--day/--night` 的 `display` 二选一，
 *   第六批起为真实素材照片），换主题是整层图换了，⛔ 不是几个颜色值在变。
 *   只给表面色加 transition、却让背景照片瞬间跳变，观感是**不一致的**。
 *   View Transitions 抓的是整棵树的快照 ⇒ 一次交叉淡入覆盖全部图层，观感统一。
 *
 * ★ 为什么是渐进增强：单文档 View Transitions 的支持面为
 *   Chrome 111+ / Safari 18+ / Firefox 144+（MDN BCD）。不支持的浏览器
 *   直接走原来的同步切换 —— ⛔ 功能不依赖它，最坏情况只是「没有过渡」。
 *
 * ★ 熔断：用户动效开关为 off、或系统 `prefers-reduced-motion: reduce` 时
 *   **不做**过渡（大范围形变对前庭敏感用户有害）。⛔ 不靠 CSS 兜底 —— 这里直接不启动。
 */
interface ViewTransitionLike {
  ready: Promise<void>;
}

type DocumentWithVT = Document & {
  startViewTransition?: (callback: () => void) => ViewTransitionLike;
};

function motionAllowed(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    if (localStorage.getItem(MOTION_STORAGE_KEY) === 'off') return false;
  } catch {
    /* 隐私模式：按「允许」处理，交给系统媒体查询兜底 */
  }
  return !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * 以（可选的）圆形揭示执行一次状态变更。
 *
 * @param apply     真正改主题的同步回调（⛔ 必须同步，View Transitions 的约束）
 * @param origin    揭示圆心；缺省则退化为整页交叉淡入
 */
export function withThemeTransition(apply: () => void, origin?: { x: number; y: number }): void {
  const doc = document as DocumentWithVT;

  if (typeof doc.startViewTransition !== 'function' || !motionAllowed()) {
    apply();
    return;
  }

  const transition = doc.startViewTransition(apply);

  if (!origin) return;

  transition.ready
    .then(() => {
      const { innerWidth: w, innerHeight: h } = window;
      // 半径取「圆心到最远角」⇒ 揭示必然覆盖整屏，不会留下未更新的角落
      const radius = Math.hypot(Math.max(origin.x, w - origin.x), Math.max(origin.y, h - origin.y));
      document.documentElement.animate(
        {
          clipPath: [
            `circle(0px at ${origin.x}px ${origin.y}px)`,
            `circle(${radius}px at ${origin.x}px ${origin.y}px)`,
          ],
        },
        {
          // ⚠ 时长即「过渡期间页面收不到指针事件」的窗口长度（实测 Chromium 硬屏蔽命中测试，
          //    且不理会 CSS 的 pointer-events）。故此处刻意取短，并关闭容器动画。
          //    实测：无揭示动画时约 246ms；加 280–400ms 揭示后落在 650–780ms 区间（抖动大于时长差异），
    //    即**主体是浏览器固有开销**，本值只占小头 ⇒ 只能小幅度调，⛔ 不能靠它把窗口压到很低。
          //    改动该值须同步复核 `verify_deepen.py` 的 D6 阈值。
          duration: 320,
          easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
          pseudoElement: '::view-transition-new(root)',
        },
      );
    })
    .catch(() => {
      /* `ready` 在过渡被跳过时会 reject：静默即可，主题已切换 */
    });
}

/** 取元素中心（用于把揭示圆心放在被点的那枚开关上）。 */
export function centerOf(element: Element | null): { x: number; y: number } | undefined {
  if (!element) return undefined;
  const rect = element.getBoundingClientRect();
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
}
