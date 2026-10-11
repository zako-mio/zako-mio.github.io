#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内联 SVG 图件「**渲染后**缩放比」判据（浏览器实测）—— 批20.5 新增的维度。

# ─────────────────────────────────────────────────────────────────────────────
# 来源登记（Provenance）：本件是 scripts/probes/ 下的 **CI 活件**（仓库原生）。
#   · 登记表：scripts/probes/PROVENANCE.json（机检 scripts/probes/check_provenance.py）
#   · 与 CI 的一致性：scripts/check_ci_manifest.py（E1，双向 fail-closed）
#   · ⛔ 无归档冻结件：本件是**新增判据**（不是从某批归档件复制），故 origin = repo-native。
# ─────────────────────────────────────────────────────────────────────────────

判据（每条都可复跑、失败即 FAIL）：
  R1 **渲染缩放比 ≥ 1**：每个**可见**且含 `<text>` 的内联 `<svg>`，其
     `渲染宽 / viewBox 宽` 必须 ≥ 1（容差 0.999）。
     ⇒ 口径＝「**图件不得渲染到其设计尺寸以下**」。依据是**自洽**的，⛔ 不引入外部字号标准：
        图件的源字号（10–12px）是设计者选定的阅读尺寸；`width:100%` 把它等比缩小，
        渲染后文字尺寸 = 源字号 × 缩放比 —— 这个乘积**不在任何既有判据的作用面内**。
  R2 **⛔ 无整页横滚**：`documentElement.scrollWidth ≤ innerWidth + 1`。
     依据：宽内容必须落在**自己的**滚动容器里（`.figure__frame` / `.chart__frame`），
     ⛔ 不允许把整页撑出横向滚动（README「网格子项必须显式收缩」同款纪律）。

★ 为什么需要这一维（**判据作用面的缺口**，非「阈值调参」）：
  ① `svg_layout_probe` 的 S1/S2 判**源几何**（文字压框、箭头落点）—— 缩放**不改变源几何**
     ⇒ 图件缩到 4px 时 S1/S2 照样 ALL PASS；
  ② `layout_stability_probe` 判**位移**（CLS/Δ），⛔ 不判尺寸；
  ③ axe-core 覆盖 WCAG 2.2 AA —— **WCAG 没有任何一条成功准则规定最小字号**
     ⇒ 机检在结构上不可能发现它。
  ⇒ 三者实测全绿而图件在手机上完全不可读（批20.5 独立复验：390px 视口下渲染字号 4px / 缩放比 0.367）。

★ 修法与判据**必须同批**（本站纪律：改完无人守＝下次照样复发）：
  · `.figure__svg` 给 1:1 下限（`--svg-intrinsic-w` ＝ 组件 viewBox 宽）⇒ 窄视口改为横向滚动；
  · 滚动区域必须**键盘可达**（`tabindex=0` ＋ `role=group` ＋ 名称）——
    ⚠ 实测：只加 `min-width` 而不落 `tabindex` 时，axe 在同款规则集下新增
    `scrollable-region-focusable`（WCAG 2.1.1）⇒ 站点自己的 a11y 门控会判 FAIL（本批踩到）；
  · 图表（固定宽 760，无法用滚动以外的办法在小容器里保持 1:1）⇒ 窄视口改用 **HTML/CSS 条形**
    （流体 ⇒ 缩放比恒为 1），并保留宽版 SVG（可用宽 ≥ 760 时恰好 1:1）。

⚠ 声明的不覆盖面：
  ① 只判「含 `<text>` 的 svg」——纯几何图件（无文字）缩小不造成**文字**不可读，
     且图标（如 rail 的 17px 图标，viewBox 24 ⇒ 缩放 0.71）**有意**如此，纳入即假阳。
  ② 只判**可见**的 svg（`display:none` 的暗色帧与窄视口隐藏的宽版图不参与）。
  ③ ⛔ 不判**上界**（放大不算缺陷）：小容器 + 小固有宽 ⇒ 允许放大（矢量不失真）。
  ④ ⛔ 不判字号**绝对值**是否合适（8px 声明但放大到 12px 渲染属既有取舍，见 README「已知取舍」）。

用法：
    setsid python3 -m http.server 4399 --directory out >/tmp/…log 2>&1 </dev/null & disown
    python3 scripts/probes/svg_text_scale_probe.py
    python3 scripts/probes/svg_text_scale_probe.py --selftest     # 两臂：对照臂（不碰＝PASS）＋ 负向臂（复原缺陷＝FAIL）
    SITE_BASE=http://127.0.0.1:4400 python3 scripts/probes/svg_text_scale_probe.py
⛔ 只读页面，不改仓库。
"""
from __future__ import annotations

import argparse
import os
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_BASE = "http://127.0.0.1:4399"
PAGES = ["/", "/works/", "/stats/", "/about/", "/works/12-factor-methodology-kg/"]
WIDTHS = [1440, 1024, 768, 390]
TOL = 0.999  # 缩放比容差（浮点；1.0 视为达标）

JS = r"""
() => {
  const rows = [];
  for (const svg of document.querySelectorAll('svg')) {
    // ② 只判可见者：祖先 display:none 时 getBoundingClientRect 为 0 ⇒ 用尺寸过滤即可
    const r = svg.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    // ① 只判含文字的图件
    if (!svg.querySelector('text')) continue;
    const vb = (svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
    if (vb.length !== 4 || !(vb[2] > 0)) continue;
    const scale = r.width / vb[2];
    rows.push({
      cls: ((svg.getAttribute('class') || '') + '|' +
            (svg.parentElement && svg.parentElement.getAttribute('class') || '')).slice(0, 60),
      renderedW: Math.round(r.width * 100) / 100,
      viewBoxW: vb[2],
      scale: Math.round(scale * 1000) / 1000,
      nText: svg.querySelectorAll('text').length,
    });
  }
  return {
    rows,
    pageScrollW: document.documentElement.scrollWidth,
    innerW: window.innerWidth,
  };
}
"""

# ── 负向夹具：在活 DOM 上**复原被修掉的缺陷**（图件被压到设计尺寸以下）。
#    ⛔ 不是「造一个截图」，而是回到缺陷形态，再问判据抓不抓得到 —— 抓不到即判据失效（恒真）。
MUTATE = """() => {
  const svgs = [...document.querySelectorAll('svg')].filter(s => s.querySelector('text')
    && s.getBoundingClientRect().width > 1);
  if (!svgs.length) return 0;
  for (const s of svgs) { s.style.minWidth = '0px'; s.style.width = '120px'; }
  return svgs.length;
}"""


def resolve_base(cli_base: str | None) -> str:
    return cli_base or os.environ.get("SITE_BASE") or DEFAULT_BASE


def scan(pg, base: str, mutate: bool = False) -> dict:
    """跑一轮：返回 {label: {rows, pageScrollW, innerW}}；mutate=True 时先复原缺陷。"""
    out: dict = {}
    for w in WIDTHS:
        pg.set_viewport_size({"width": w, "height": 900})
        for path in PAGES:
            pg.goto(f"{base}{path}", wait_until="load", timeout=60000)
            pg.wait_for_timeout(500)
            mutated = pg.evaluate(MUTATE) if mutate else 0
            if mutate:
                pg.wait_for_timeout(200)
            r = pg.evaluate(JS)
            r["mutated"] = mutated
            out[f"{path}@{w}"] = r
    return out


def judge(runs: dict) -> tuple[list[str], list[str], int]:
    """返回 (fails, notes, 参与判定的 svg 总数)。"""
    fails: list[str] = []
    notes: list[str] = []
    total = 0
    for label, r in runs.items():
        for row in r["rows"]:
            total += 1
            if row["scale"] < TOL:
                fails.append(
                    f"R1 [{label}] 图件渲染缩放比 {row['scale']} < 1"
                    f"（渲染宽 {row['renderedW']} / viewBox 宽 {row['viewBoxW']}；{row['nText']} 段文字）"
                    f" —— {row['cls']}"
                )
        if r["pageScrollW"] > r["innerW"] + 1:
            fails.append(
                f"R2 [{label}] 整页出现横向滚动：scrollWidth {r['pageScrollW']} > innerWidth {r['innerW']}"
            )
    counts = ", ".join(f"{k}={len(v['rows'])}" for k, v in runs.items() if v["rows"])
    notes.append(f"参与判定的内联文字图件：{total} 处（{counts or '无'}）")
    return fails, notes, total


def selftest(base: str) -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        ctx.add_init_script("localStorage.setItem('ui-theme','light')")
        page = ctx.new_page()

        # 对照臂：不碰页面 ⇒ 判据应当通过（证明它不是在无脑报错）
        clean_runs = scan(page, base, mutate=False)
        clean_fails, _, clean_total = judge(clean_runs)
        print(f"  [{'PASS' if not clean_fails and clean_total else 'FAIL'}] "
              f"对照臂（未改动）：fails={len(clean_fails)} 参与判定={clean_total}")

        # 负向臂：复原「图件被压到设计尺寸以下」⇒ 判据必须抓到
        bad_runs = scan(page, base, mutate=True)
        bad_fails, _, bad_total = judge(bad_runs)
        r1_hit = [f for f in bad_fails if f.startswith("R1")]
        print(f"  [{'PASS' if r1_hit else 'FAIL'}] 负向臂（压到 120px）：R1 命中 {len(r1_hit)} 条"
              f"{'，例：' + r1_hit[0][:110] if r1_hit else ''}")

        # R2 负向臂：让整页横向溢出 ⇒ R2 必须抓到
        page.set_viewport_size({"width": 390, "height": 900})
        page.goto(f"{base}/", wait_until="load", timeout=60000)
        page.wait_for_timeout(400)
        page.evaluate("() => { const d=document.createElement('div'); d.style.cssText='width:1200px;height:10px'; document.body.appendChild(d); }")
        page.wait_for_timeout(200)
        r2_hit = [f for f in judge({"/@390": page.evaluate(JS)})[0] if f.startswith("R2")]
        print(f"  [{'PASS' if r2_hit else 'FAIL'}] 负向臂（插 1200px 块）：R2 命中 {len(r2_hit)} 条")

        ctx.close()
        browser.close()
    ok = (not clean_fails) and bool(clean_total) and bool(r1_hit) and bool(r2_hit)
    print(f"\nSELFTEST: {'ALL PASS' if ok else 'HAS FAILURE'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="内联 SVG 图件渲染后缩放比判据（R1 缩放比 ≥ 1 · R2 ⛔ 无整页横滚）")
    ap.add_argument("base", nargs="?", default=None,
                    help=f"站点基址（缺省 {DEFAULT_BASE}；亦可由 SITE_BASE 环境变量给出）")
    ap.add_argument("--selftest", action="store_true",
                    help="两臂自检：对照臂（未改动须 PASS）＋ 负向夹具（复原缺陷须被抓到）")
    args = ap.parse_args()
    base = resolve_base(args.base)

    if args.selftest:
        return selftest(base)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        ctx.add_init_script("localStorage.setItem('ui-theme','light')")
        page = ctx.new_page()
        runs = scan(page, base, mutate=False)
        ctx.close()
        browser.close()

    fails, notes, total = judge(runs)
    for n in notes:
        print(f"  [info] {n}")
    if total == 0:
        print("  [FAIL] R3 非空守卫：一个「含文字的内联 SVG」都没扫到 ⇒ 判据在此哑火，⛔ 不得静默通过")
        return 2
    for f in fails:
        print(f"  [FAIL] {f}")
    print(f"\nSVG-TEXT-SCALE: {'ALL PASS' if not fails else f'HAS FAILURE ({len(fails)})'}")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
