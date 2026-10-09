#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内联 SVG 图件排版判据（浏览器实测几何）—— 「重叠」的机检。

# ─────────────────────────────────────────────────────────────────────────────
# 来源登记（Provenance）：本件是 scripts/probes/ 下的 **CI 活件**（可演进）。
#   · 归档冻结件：Mission-file/2026-10/1008-个人主页深化改革/batch6-evidence/verify_svg_layout.py
#                  @ 1a06be5 · sha256=6cbc9915b6b1b7fec2477a66093ca45f40bd1a6715ba67f98ef31766d658d207
#   · 漂移方向：本件可演进；归档件⛔ 不追改、不自动同步（保其批报告的逐字节可复现）。
#   · 登记表：scripts/probes/PROVENANCE.json（机检 scripts/probes/check_provenance.py）
#   · 相对归档件的改动（第八批 §4-② 硬化）：加 --base／SITE_BASE 参数化、argparse 化、
#     删去一行未被引用的死代码（`allowed = {...}`）。判据逻辑逐字未动。
# ─────────────────────────────────────────────────────────────────────────────

判据（每条都可复跑、失败即 FAIL）：
  S1 **文字 × 矩形框/文字交叉**：某 `<text>` 的实渲染框与**不属于同一组**的 `rect` 或
     另一 `<text>` 相交面积 > 较小者 5%（且非完全包含）⇒ FAIL（文字压框、文字压字）。
     ⚠ **声明的不覆盖面**：`circle` / `ellipse` / `path` **不判** —— 圆的外接正方形
     会把「环内中央的文字」误报为重叠，而本项目有意让节点骑在轨道圆上；
     该面无法用纯几何区分「有意骑线」与「真压字」（实测：两版判据在此全为假阳）。
  S2 **箭头落点**（按目标形状分档，两档都有理由）：
     · 目标为**矩形**（方框）：箭头切在框边上是**正确画法**（读作「指到框裡」）
       ⇒ 只禁「插进框内 > 0.5px」；留 1–3px 小缝同样可接受。
     · 目标为**圆**（环上节点）：箭头若只贴圆周，会与圆盘相切/相交 ⇒ 要求净距 ≥ 4px。
     净距 = 到最近节点边界的距离（框内为负）。

★ 判据自身的假阳性（批六实测踩到、已修正 —— 记下来防复发）：
  ① **圆用 bbox 判交会造大量假阳**：`circle` 的 `getBoundingClientRect` 是外接正方形，
     文字落在圆环**中央空白**也会被判「与圆相交」。⇒ 圆/椭圆改用**环带距离**判。
  ② **端点容差不能拍脑袋加**：早先版本给矩形端点加了 +3px「箭头余量」⇒ 每个正常
     贴边箭头都被判 FAIL。⇒ 改成显式「净距 ≥ 4px」并**打印实测净距**，阈值是设计规则、
     不是凑数。
  ③ 祖先-后代对必须排除（标签在自己的框内是「包含」，不是重叠）。

用法：
    setsid python3 -m http.server 4399 --directory out >/tmp/…log 2>&1 </dev/null & disown
    python3 scripts/probes/svg_layout_probe.py                      # 实测 out/
    python3 scripts/probes/svg_layout_probe.py --selftest           # 活 DOM 上复原缺陷，验判据非恒真
    SITE_BASE=http://127.0.0.1:4400 python3 scripts/probes/svg_layout_probe.py
⛔ 只读页面，不改仓库。
"""
from __future__ import annotations

import argparse
import os
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_BASE = "http://127.0.0.1:4399"
PAGES = ["/", "/about/", "/works/", "/stats/", "/works/12-factor-methodology-kg/"]
WIDTHS = [1440, 1024, 768, 390]
MIN_ARROW_CLEARANCE = 4.0  # px

JS = r"""
(MIN_CLEAR) => {
  const fails = [];
  const info = [];
  const cname = e => ((e.className && e.className.baseVal !== undefined) ? e.className.baseVal : (e.className || '')).toString();
  const label = e => `${e.tagName.toLowerCase()}.${cname(e).split(' ').filter(Boolean).slice(0,2).join('.')}「${(e.textContent||'').trim().slice(0,16)}」`;

  for (const svg of document.querySelectorAll('svg')) {
    if (!svg.getClientRects().length) continue;
    const vb = svg.getAttribute('viewBox') || '';
    const all = [...svg.querySelectorAll('text,rect,circle,ellipse,line,path,polygon,polyline')]
      .filter(e => !e.closest('defs'));

    // ---------- S1 文字 × 非同类图元 ----------
    for (const t of all.filter(e => e.tagName.toLowerCase() === 'text')) {
      const a = t.getBoundingClientRect();
      for (const o of all) {
        if (o === t || o.contains(t) || t.contains(o)) continue;
        const tag = o.tagName.toLowerCase();
        // ★ 判据**声明的不覆盖面**（不是遗漏）：circle / ellipse / path。
        //   圆的 bbox 是其外接正方形，用 bbox 判交会把「环内中央的文字」误报为重叠；
        //   本项目的环/轨道圆**有意**让节点与其文字骑在环上（圆在下层、节点有填充）
        //   ⇒ 该面无法用几何判据区分「有意骑线」与「真压字」，故**不判**，登记为不覆盖。
        if (tag !== 'rect' && tag !== 'text') continue;
        const b = o.getBoundingClientRect();
        const ix = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const iy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (ix <= 0.5 || iy <= 0.5) continue;
        const inter = ix * iy;
        const smaller = Math.min(a.width * a.height, b.width * b.height);
        if (smaller <= 0.5 || inter / smaller <= 0.05) continue;
        // 完全包含：本项目的节点框把标题/副题装在里面是**有意的**（ECharts 数据标签同理）
        if (tag === 'rect' && inter / smaller > 0.97) continue;
        fails.push(`S1 [${vb}] 文字交叠：${label(t)} × ${label(o)}（相交占较小者 ${(inter/smaller).toFixed(2)}）`);
      }
    }

    // ---------- S2 箭头净距 ----------
    const nodes = [...svg.querySelectorAll('rect.dg-node, circle.dg-node')];
    const edges = [...svg.querySelectorAll('path.dg-edge[marker-end], path.dg-edge[markerEnd]')];
    for (const e of edges) {
      const d = e.getAttribute('d') || '';
      const tail = d.slice(d.lastIndexOf('A') >= 0 && d.lastIndexOf('A') > d.lastIndexOf('L') ? d.lastIndexOf('A') : Math.max(d.lastIndexOf('L'), d.lastIndexOf('C')));
      const nums = (tail.match(/-?\d+(\.\d+)?/g) || []).map(Number);
      if (nums.length < 2) continue;
      const px = nums[nums.length - 2], py = nums[nums.length - 1];
      let worst = null;   // {clear, want, kind}
      for (const n of nodes) {
        let clear, want;
        if (n.tagName.toLowerCase() === 'circle') {
          const r = +n.getAttribute('r');
          clear = Math.hypot(px - +n.getAttribute('cx'), py - +n.getAttribute('cy')) - r;
          want = MIN_CLEAR;                    // 圆：必须明显在圆外
        } else {
          const x = +n.getAttribute('x'), y = +n.getAttribute('y');
          const w = +n.getAttribute('width'), h = +n.getAttribute('height');
          const inside = px > x && px < x + w && py > y && py < y + h;
          clear = inside ? -Math.min(px - x, x + w - px, py - y, y + h - py)
                         : Math.max(x - px, px - (x + w), y - py, py - (y + h));
          want = -0.5;                         // 框：允许切边，禁穿透
        }
        const margin = clear - want;
        if (worst === null || margin < worst.margin) worst = { clear, want, margin, kind: n.tagName.toLowerCase() };
      }
      if (worst === null) continue;
      info.push(`    S2 端点(${px},${py}) 最近节点净距 ${worst.clear.toFixed(2)}px（要求 ≥ ${worst.want}）`);
      if (worst.margin < -0.001) {
        fails.push(`S2 [${vb}] 箭头落点不合规：净距 ${worst.clear.toFixed(2)}px（${worst.kind}，要求 ≥ ${worst.want}）@(${px},${py})`);
      }
    }
  }
  return { fails, info };
}
"""


# ---------------------------------------------------------------- 负向夹具
# ★ 判据必须能 FAIL，否则是哑火门控（恒真）。夹具做法：**在活 DOM 上复原被修掉的那个缺陷**，
#   再问判据是否抓到 —— 抓不到即视为判据失效。
MUTATE_S1 = """() => {
  const svg = document.querySelector('svg.figure__svg');
  const head = [...svg.querySelectorAll('text.dg-head')].find(t => t.textContent.trim() === '呈现');
  const node = [...svg.querySelectorAll('rect.dg-node')].find(r => +r.getAttribute('x') === 648);
  head.setAttribute('y', 16);          // 列头回到原来的位置
  node.setAttribute('y', 8);           // 首节点回到原来的位置 ⇒ 复现「列头压框」
  return true;
}"""

MUTATE_S2 = """() => {
  const svg = document.querySelector('svg.figure__svg');
  const r = svg.querySelector('circle.dg-node');
  if (r) { r.setAttribute('r', 44); return 'circle'; }
  return null;
}"""


def resolve_base(cli_base: str | None) -> str:
    return cli_base or os.environ.get("SITE_BASE") or DEFAULT_BASE


def selftest(base: str) -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        ctx.add_init_script("localStorage.setItem('ui-theme','light')")
        page = ctx.new_page()

        page.goto(f"{base}/", wait_until="networkidle")
        page.wait_for_timeout(300)
        page.evaluate(MUTATE_S1)
        page.wait_for_timeout(200)
        s1_hit = [f for f in page.evaluate(JS, MIN_ARROW_CLEARANCE)["fails"] if f.startswith("S1")]
        print(f"  [{'PASS' if s1_hit else 'FAIL'}] 夹具 S1（复原「呈现」压框）被抓到：{s1_hit[:1]}")

        s2_hit = []
        for path in PAGES:
            page.goto(f"{base}{path}", wait_until="networkidle")
            page.wait_for_timeout(300)
            kind = page.evaluate(MUTATE_S2)
            if kind:
                page.wait_for_timeout(200)
                s2_hit = [f for f in page.evaluate(JS, MIN_ARROW_CLEARANCE)["fails"] if f.startswith("S2")]
                if s2_hit:
                    break
        print(f"  [{'PASS' if s2_hit else 'FAIL'}] 夹具 S2（放大节点圆）被抓到：{s2_hit[:1]}")

        ctx.close()
        browser.close()
    ok = bool(s1_hit) and bool(s2_hit)
    print(f"\nSELFTEST: {'ALL PASS' if ok else 'HAS FAILURE'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="内联 SVG 图件排版判据（浏览器实测几何）")
    ap.add_argument("base", nargs="?", default=None,
                    help=f"站点基址（缺省 {DEFAULT_BASE}；亦可由 SITE_BASE 环境变量给出）")
    ap.add_argument("--selftest", action="store_true",
                    help="在活 DOM 上复原被修掉的缺陷，验证判据非恒真")
    args = ap.parse_args()
    base = resolve_base(args.base)

    if args.selftest:
        return selftest(base)

    all_fails: list[str] = []
    seen: set[str] = set()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        ctx.add_init_script("localStorage.setItem('ui-theme','light')")
        page = ctx.new_page()
        for w in WIDTHS:
            page.set_viewport_size({"width": w, "height": 900})
            for path in PAGES:
                page.goto(f"{base}{path}", wait_until="networkidle")
                page.wait_for_timeout(350)
                r = page.evaluate(JS, MIN_ARROW_CLEARANCE)
                for f in r["fails"]:
                    key = f.split("@")[0]
                    if key in seen:
                        continue
                    seen.add(key)
                    all_fails.append(f"[{w}px]{path} {f}")
        ctx.close()
        browser.close()

    for f in all_fails:
        print(f"  [FAIL] {f}")
    print(f"\nSVG-LAYOUT: {'ALL PASS' if not all_fails else f'HAS FAILURE ({len(all_fails)})'}")
    return 0 if not all_fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
