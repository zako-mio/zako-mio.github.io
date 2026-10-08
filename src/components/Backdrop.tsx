import { BackdropFx } from './BackdropFx';

/**
 * 背景系统（第六批 · 真实公开素材替换「自绘」背景）。
 *
 * ★ 为什么换掉第五批的纯 CSS 背景：它由 `radial-gradient` 点阵 + 大面积柔光斑拼成，
 *   本质是「自己画的」——放大后没有可分辨的细节，观感发虚（用户走查判定）。
 *   本批改为**真实公开素材**，清晰度由原图分辨率决定：
 *     · `--night`：ESO eso0934a《A 340-million pixel starscape from Paranal》
 *       真实银河照片（CC BY 4.0 —— 署名见页脚）。
 *     · `--day`：CC0 极光天幕经**亮度派生**出的浅色纱幕
 *       （暗天空归白 ⇒ 不在浅色页底压出灰幕；派生公式见
 *       `build_backdrop_assets.py`，产物 `public/backdrop/*.webp`）。
 *
 * ★ 两帧的显隐**由主题选择器决定、不由 JS 决定**（同 `.chart__frame` 的既有口径）：
 *   非当前主题的一帧 `display:none` ⇒ 浏览器**不会下载**它的图（每主题只拉一份）。
 *   ⛔ 不要改成「两帧都挂 opacity」——那会把两份素材都拉下来。
 *
 * ★ 动效只做 `transform`（慢速漂移，合成层）；`prefers-reduced-motion: reduce`
 *   与 `[data-motion='off']` 由全局熔断规则兜底（见 globals.css 动效层）。
 *
 * ★ `aria-hidden` + 无文本 ⇒ 不进可访问性树，不影响「无 JS 可读」（冒烟 S6）。
 */
export function Backdrop() {
  return (
    <div className="backdrop" aria-hidden="true">
      <span className="backdrop__photo backdrop__photo--day" />
      <span className="backdrop__photo backdrop__photo--night" />
      <span className="backdrop__veil backdrop__veil--day" />
      <span className="backdrop__veil backdrop__veil--night" />
      <span className="backdrop__grid" />
      <span className="backdrop__meteors">
        <i className="backdrop__meteor backdrop__meteor--1" />
        <i className="backdrop__meteor backdrop__meteor--2" />
        <i className="backdrop__meteor backdrop__meteor--3" />
      </span>
      {/* 星野特效层：只在夜间挂载、且受 reduced-motion / 动效开关熔断（见 BackdropFx.tsx）。 */}
      <BackdropFx />
    </div>
  );
}
