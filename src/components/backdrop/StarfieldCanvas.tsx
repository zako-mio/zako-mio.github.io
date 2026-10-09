'use client';

/**
 * 夜间星野（tsparticles）—— 客户端渲染、懒加载、可交互。
 *
 * ★ 素材来源：`tsparticles`（MIT）的官方 `preset-stars`（`@tsparticles/preset-stars`）。
 *   本站**没有**自己画星（那是批五被走查否掉的「自绘点阵」）；这里只用官方预设 +
 *   极少量贴合本站主题的覆盖项，且覆盖项逐条有理由（见 OPTIONS 注释）。
 *
 * ★ 清晰度：`detectRetina` ⇒ 画布按 `devicePixelRatio` 放大、粒子按设备像素画
 *   ⇒ 在 2x/3x 屏上是**锐利圆点**，不是被拉伸的低像素贴图。
 *   ⚠ 批十起为**按输入能力分档**（见下）：只有精确指针档才开 retina。
 *
 * ★ 可交互：`detectsOn: 'window'` —— 背景层是 `pointer-events:none` 且在 `z-index:-1`，
 *   画布本身收不到指针事件，只有挂在 window 上才算得到真实光标位置（悬停连线）。
 *
 * ★ 懒加载：引擎与预设体积不小，故用 `next/dynamic({ ssr:false })` 延后到水合之后，
 *   ⛔ 不把粒子塞进首屏 JS（首屏预算 106 kB 是本站硬约束）。
 *
 * ★ 输入能力分档（★ 批十，用户实测驱动）：`FINE_POINTER` ＝ 精确指针 + 悬停能力。
 *   · `onHover.enable` 只在 `FINE_POINTER` 时为真 —— tsParticles 的 `onHover` 会被
 *     `touchstart`/`touchmove` 一起喂坐标（bundle 内 `touchStartEvent`/`touchMoveEvent`），
 *     ⇒ **触屏上手指按住背景即触发 `grab` 连线**。实测（本机 100% 复现）：
 *     连线像素 **0 → 8 128**、canvas 非透明像素 **1 095 → 12 116（≈11×）**、
 *     对照臂噪声为 0。用户机型（华为畅享70X / HarmonyOS 4.2 / 微信浏览器）与「别人也反馈手机卡」一致。
 *     ⇒ 判据是「**悬停语义不该在没有悬停能力的输入上生效**」，与 `.backdrop__glow`
 *       的「触屏不启用」是**同一口径**（该层已用 `@media (hover:hover) and (pointer:fine)` 门控）。
 *   · `detectRetina` 在触屏下关掉（DPR 回 1）：画布是**全屏每帧重绘**，3x 屏下栅格化面积
 *     约为 1x 的 9 倍，是入门机掉帧的另一条独立成本。⚠ **代价**：星点在非 retina 画布上
 *     会被浏览器放大 ⇒ 略柔（与 README 早先「2x/3x 屏上锐利圆点」的表述相抵）—— 若观感不可接受，
 *     把它改回 `true` 即可（`onHover` 那条与它无关，⛔ 不要一起回退）。
 *
 * ★★ 批十一 · 真机归因分离（进行中，⚠ 这是一次**有意的临时 A/B**）：
 *   `be457d8` **同时**上了「关 `grab`」与「关 `detectRetina`」两项缓解，用户真机裁定「不卡了」，
 *   但**不知是哪一项生效** ⇒ 若主因是「关 grab」，则 retina 降档是**不必要的代价**（星点变柔）。
 *   ⇒ 本批把 `detectRetina` **改回 `true`（触屏也开 retina）**、部署后请用户在同一机型实测：
 *     · 仍不卡 ⇒ **保留 `true`**（拿回锐利星点），结论＝「`grab` 是主因，retina 无关」；
 *     · 又卡   ⇒ 改回 `FINE_POINTER`，结论＝「两者共同作用，retina 降档必要」。
 *   ⛔ **无论结果如何，`onHover.enable = FINE_POINTER` 都不改回** —— 那是**正确性**主张
 *     （悬停语义不该在没有悬停能力的输入上生效），不是性能手段；两者混谈会变成
 *     「为了性能把正确性回退」（b102：一次只改一个因子）。
 *   ⚠ 待办：真机结论出来后，把本段改成结论陈述（含机型与部署 sha）。
 *
 * ★ 熔断：`prefers-reduced-motion: reduce` 或 `[data-motion='off']` 时**根本不挂载**
 *   （见 BackdropFx.tsx 的门）；★ 批十：「动效开」(`data-motion='on'`) 可覆盖 OS 的 reduce。
 */
import { Particles, ParticlesProvider } from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';
import { loadStarsPreset } from '@tsparticles/preset-stars';

/**
 * ⚠ `ParticlesProvider` 的 `init` 必须是**模块级稳定引用**：
 *   其实现里有「init 回调跨生命周期不一致即抛错」的断言，且引擎初始化是**单例**。
 */
const initEngine = async (engine: Parameters<typeof loadSlim>[0]): Promise<void> => {
  await loadSlim(engine);
  await loadStarsPreset(engine);
};

/** 本件经 `next/dynamic({ssr:false})` 懒加载 ⇒ 模块求值期已在浏览器；仍做防御性判断。 */
const FINE_POINTER =
  typeof window !== 'undefined' &&
  window.matchMedia('(hover: hover) and (pointer: fine)').matches;

const OPTIONS = {
  // 预设自带 `fullScreen: true` 与黑色背景 ⇒ 必须关掉并由本站容器接管尺寸/底色
  fullScreen: { enable: false },
  preset: 'stars',
  // ★ 批十一 · 真机归因分离（临时 A/B）：改回 `true` ⇒ 触屏也开 retina（拿回锐利星点）。
  //   ⚠ 待真机裁定：仍不卡 ⇒ 保留；又卡 ⇒ 改回 `FINE_POINTER`。参见文件头注。
  //   ⛔ 与下面 `onHover.enable` 那条**分开裁决**（后者是正确性主张，永不改回）。
  detectRetina: true,
  fpsLimit: 60,
  background: { color: { value: 'transparent' } },
  particles: {
    // 预设 100 颗对整页太稀；620（经 density 折算后在 1440×900 上约 390 颗）
    // 是「布满但不成噪点」的实拍取值 —— 260 实测偏稀，肉眼可数。
    number: { value: 620, density: { enable: true, width: 1920, height: 1080 } },
    // 预设是纯白；加三种偏冷/偏暖的星色，与本站暗色令牌同族（更像真实星空）
    color: { value: ['#ffffff', '#d6e4ff', '#ffe9c9', '#a9c6ff'] },
    size: { value: { min: 0.5, max: 2.4 } },
    opacity: {
      value: { min: 0.18, max: 1 },
      // 闪烁：预设已开 animation，这里只把速度压慢（快闪像噪点）
      animation: { enable: true, speed: 0.5, sync: false, startValue: 'random' },
    },
    // 预设 speed 0.1；保持极慢漂移（观感是「星空在转」，不是「粒子在飞」）
    move: { enable: true, speed: 0.1, direction: 'none' as const, random: true, straight: false },
    links: { enable: false }, // 常态不连线（会变成「星座网」，与 Hero 的星轨图件抢注意力）
    shape: { type: 'circle' },
  },
  interactivity: {
    detectsOn: 'window' as const,
    events: {
      // ★ 批十：**触屏不启用** —— 悬停语义不该在没有悬停能力的输入上生效
      //   （tsParticles 的 onHover 会被 touchstart/touchmove 触发 ⇒ 手机按住背景即拉线 ≈11× 绘制量）。
      onHover: { enable: FINE_POINTER, mode: 'grab' },
      onClick: { enable: false },
      resize: { enable: true },
    },
    modes: {
      // ★ 第八批（裁决④ · T2）：**只调「可发现性」这一维，不加新效果类型、不加依赖**。
      //   实测原档 grab.distance=190 / links.opacity=0.22 在 1440×900 上「要恰好碰到星点才出现」，
      //   等于不可发现 ⇒ 扩大响应半径并提高连线可见度（仍是同一模式、0 新增字节）。
      grab: { distance: 260, links: { opacity: 0.45, color: '#9fc0ff' } },
    },
  },
};

export default function StarfieldCanvas() {
  return (
    <ParticlesProvider init={initEngine}>
      <Particles id="backdrop-stars" className="backdrop__fx-canvas" options={OPTIONS} />
    </ParticlesProvider>
  );
}
