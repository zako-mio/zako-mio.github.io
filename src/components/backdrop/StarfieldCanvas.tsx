'use client';

/**
 * 夜间星野（tsparticles）—— 客户端渲染、懒加载、可交互。
 *
 * ★ 素材来源：`tsparticles`（MIT）的官方 `preset-stars`（`@tsparticles/preset-stars`）。
 *   本站**没有**自己画星（那是批五被走查否掉的「自绘点阵」）；这里只用官方预设 +
 *   极少量贴合本站主题的覆盖项，且覆盖项逐条有理由（见 OPTIONS 注释）。
 *
 * ★ 清晰度：`detectRetina: true` ⇒ 画布按 `devicePixelRatio` 放大、粒子按设备像素画
 *   ⇒ 在 2x/3x 屏上是**锐利圆点**，不是被拉伸的低像素贴图。
 *
 * ★ 可交互：`detectsOn: 'window'` —— 背景层是 `pointer-events:none` 且在 `z-index:-1`，
 *   画布本身收不到指针事件，只有挂在 window 上才算得到真实光标位置（悬停连线）。
 *
 * ★ 懒加载：引擎与预设体积不小，故用 `next/dynamic({ ssr:false })` 延后到水合之后，
 *   ⛔ 不把粒子塞进首屏 JS（首屏预算 106 kB 是本站硬约束）。
 *
 * ★ 熔断：`prefers-reduced-motion: reduce` 或 `[data-motion='off']` 时**根本不挂载**
 *   （见 BackdropFx.tsx 的门），退化路径是「没有特效」，⛔ 不是「没有背景」。
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

const OPTIONS = {
  // 预设自带 `fullScreen: true` 与黑色背景 ⇒ 必须关掉并由本站容器接管尺寸/底色
  fullScreen: { enable: false },
  preset: 'stars',
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
      onHover: { enable: true, mode: 'grab' }, // 唯一的交互：悬停时与邻近星点拉出细线
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
