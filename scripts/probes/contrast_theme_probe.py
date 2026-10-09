#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""**合成后**对比度实测（**双主题**）。

# ─────────────────────────────────────────────────────────────────────────────
# 来源登记（Provenance）：本件是 scripts/probes/ 下的 **CI 活件**（可演进）。
#   · 归档冻结件：Mission-file/2026-10/1008-个人主页深化改革/batch6-evidence/contrast_probe_theme.py
#                  @ 1a06be5 · sha256=2d3bd68731acef1ff227ac8080c2c96de9e36fcc6128e1744ae6baf59b3e084b
#   · 漂移方向：本件可演进；归档件⛔ 不追改、不自动同步（保其批报告的逐字节可复现）。
#   · 登记表：scripts/probes/PROVENANCE.json（机检 scripts/probes/check_provenance.py）
#   · 相对归档件的改动（第八批 §4-② 硬化）：① BASE 改为 --base／SITE_BASE 参数化；
#     ② 把「逐页取样→判 FAIL」抽为 analyse()／probe_page() 纯函数，判据逻辑逐字未动；
#     ③ 新增 --selftest（合成页负向夹具）。⛔ 判据数值（阈值/采样带/分类）一字未改。
# ─────────────────────────────────────────────────────────────────────────────

为什么要有这一版：
  · `scripts/gate_contrast.py` 只校**令牌对**（前景 hex × 表面 hex），看不到正文压在**照片**上这一段。
  · 第六批把背景换成**真实素材**：夜间是 ESO 银河**照片**（大面积中高亮度星云），
    比原来的深色渐变亮得多 ⇒ **暗色首次成为对比度风险面**，必须同时被实测覆盖。

采样口径沿用批五（三条防偏差设计原样保留）：
  1. ⛔ 不取「字缝间最亮像素」（那是最佳情况）；✅ 文字置透明后在同一位置取**最暗**背景像素。
  2. ⛔ 不按容器包围盒采样（会混入装饰件）；✅ 只取叶子级文本元素 + 中央带（纵向 25–75%、横向 10–90%）。
  3. 阈值：三级灰属非正文 ⇒ 3.0；其余正文 4.5；大字号按 WCAG 大文本 ⇒ 3.0。
  ★ 逐主题输出，且任一样本低于阈值即 FAIL（不分主题）。

⚠ **声明的不覆盖面**（批八 E4/E5 登记，本轮不变）：本探针①采样选择器**不含 SVG `<text>`**；
   ②**不移动指针** ⇒ 指针光斑不在其采样面内。两处靠定向实测补位，⛔ 不读作「已覆盖」。

用法：
    setsid python3 -m http.server 4399 --directory out >/tmp/…log 2>&1 </dev/null & disown
    python3 scripts/probes/contrast_theme_probe.py                # 实测 out/
    python3 scripts/probes/contrast_theme_probe.py --selftest     # 合成页负向夹具（不访问站点）
    SITE_BASE=http://127.0.0.1:4400 python3 scripts/probes/contrast_theme_probe.py
⛔ 只读页面，不改仓库；在 prefers-reduced-motion: reduce 下采样（拿终态，避开进场动画）。
"""
from __future__ import annotations

import argparse
import io
import os
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_BASE = "http://127.0.0.1:4399"
PAGES = [("/", "首页"), ("/works/", "作品"), ("/about/", "关于"), ("/stats/", "聚合")]
THEMES = ["light", "dark"]
SELECTOR = "p,h1,h2,h3,h4,li,a,span,code,td,th,dt,dd,figcaption,summary,strong,em"
BODY_MIN = 4.5
NONBODY_MIN = 3.0
TERTIARY_RGB = {
    "light": (95, 109, 132),  # --text-tertiary
    "dark": (142, 156, 179),  # --text-tertiary（深色块）
}


def _srgb(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb) -> float:
    return 0.2126 * _srgb(rgb[0]) + 0.7152 * _srgb(rgb[1]) + 0.0722 * _srgb(rgb[2])


def contrast(a, b) -> float:
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def parse_color(value: str):
    if value.startswith("rgb"):
        nums = value[value.index("(") + 1 : value.index(")")].replace(",", " ").split()
        return tuple(int(float(n)) for n in nums[:3])
    return None


COLLECT_JS = """(sel) => {
  const all = [];
  for (const el of document.querySelectorAll(sel)) {
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    if (Number(cs.opacity) < 0.6) continue;
    const text = Array.from(el.childNodes)
      .filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (!text) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 6) continue;
    all.push({
      tag: el.tagName.toLowerCase(),
      cls: (typeof el.className === 'string' ? el.className : '').split(' ').slice(0, 2).join('.'),
      color: cs.color,
      fontSize: parseFloat(cs.fontSize),
      fontWeight: cs.fontWeight,
      text: text.slice(0, 34),
      x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height,
    });
  }
  return all;
}"""

BLANK_JS = """() => {
  const s = document.createElement('style');
  s.textContent = `
    *,*::before,*::after{color:transparent !important;-webkit-text-fill-color:transparent !important;text-shadow:none !important;}
    svg{opacity:0 !important;}
    .rail__link::before,.milestones__item::before,.milestones::before,.hero__eyebrow::before,
    .section__title::after,.threads--rail::before,.theme-toggle__dot{background:transparent !important;box-shadow:none !important;}
  `;
  document.head.appendChild(s);
}"""


def resolve_base(cli_base: str | None) -> str:
    return cli_base or os.environ.get("SITE_BASE") or DEFAULT_BASE


def analyse(img, rects, tertiary, label, width, theme):
    """逐样本取「最暗背景」算对比度，低于阈值即记 FAIL。判据逻辑与归档件逐字等价。"""
    iw, ih = img.size
    worst: dict[str, tuple] = {}
    page_failures: list[str] = []
    for r in rects:
        fg = parse_color(r["color"])
        if fg is None:
            continue
        big = r["fontSize"] >= 24 or (
            r["fontSize"] >= 18.66 and int(r["fontWeight"]) >= 700
        )
        key = "非正文" if (big or fg == tertiary) else "正文"
        threshold = NONBODY_MIN if key == "非正文" else BODY_MIN

        bx0 = r["x"] + r["w"] * 0.10
        bx1 = r["x"] + r["w"] * 0.90
        by0 = r["y"] + r["h"] * 0.25
        by1 = r["y"] + r["h"] * 0.75
        # ⚠ 上界必须收到 iw-1 / ih-1：`min(iw, bx1)` 在元素贴到画布边缘时
        #   会让 y1 == ih，而 `range(y0, y1 + 1, 2)` 会取到越界索引
        #   （实测踩到：加 min-width 后表格单元格贴边 ⇒ IndexError）。
        x0, x1 = int(max(0, bx0)), int(min(iw - 1, bx1))
        y0, y1 = int(max(0, by0)), int(min(ih - 1, by1))
        if x1 <= x0 or y1 <= y0:
            continue
        local = None
        for y in range(y0, y1 + 1, 2):
            for x in range(x0, x1 + 1, 2):
                bg = img.getpixel((x, y))
                c = contrast(fg, (int(bg[0]), int(bg[1]), int(bg[2])))
                if local is None or c < local[0]:
                    local = (c, f"#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}")
        if local is None:
            continue
        if key not in worst or local[0] < worst[key][0]:
            worst[key] = (local[0], local[1], r["text"][:22])
        if local[0] < threshold:
            page_failures.append(
                f"[{theme}] {label}@{width} [{key}] {local[0]:.2f} < {threshold} "
                f"(bg {local[1]}, fg #{fg[0]:02x}{fg[1]:02x}{fg[2]:02x}, "
                f"{r['tag']}.{r['cls']}, {r['fontSize']:.0f}px) 「{r['text'][:22]}」"
            )
    return worst, page_failures


def probe_page(page, theme, tertiary, label, width):
    """对当前页面取样：收集文本 → 置透明 → 截图 → 判。返回 (worst, failures)。"""
    rects = page.evaluate(COLLECT_JS, SELECTOR)
    page.evaluate(BLANK_JS)
    page.wait_for_timeout(120)
    img = Image.open(io.BytesIO(page.screenshot(full_page=True))).convert("RGB")
    return analyse(img, rects, tertiary, label, width, theme)


# ---------------------------------------------------------------- selftest
# ★ 判据必须能 FAIL，否则是哑火门控（恒真）。合成页放一对「同字号、不同对比度」的正文，
#   问判据是否只把低对比度那个判 FAIL。⚠ 声明：本夹具覆盖「取样→最暗像素→阈值分类」这一段，
#   **不覆盖**站点真实主题/localStorage/照片背景路径（那由每次 CI 的实测覆盖）。
SELFTEST_HTML = """<!doctype html><html lang="zh"><head><meta charset="utf-8"><style>
  html,body{margin:0;padding:0;background:#ffffff;}
  p{margin:0;padding:10px;font:16px/1.5 sans-serif;}
  #hi{color:#111111;}
  #lo{color:#8a8a8a;}
</style></head><body>
  <p id="hi">high contrast sample text</p>
  <p id="lo">low contrast sample text</p>
</body></html>"""


def selftest() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 800, "height": 300})
        page.set_content(SELFTEST_HTML, wait_until="load")
        page.wait_for_timeout(150)
        _, failures = probe_page(page, "light", TERTIARY_RGB["light"], "selftest", 800)
        page.close()
        browser.close()

    lo = [f for f in failures if "low contrast" in f]
    hi = [f for f in failures if "high contrast" in f]
    checks = [
        ("负向夹具：低对比度正文（#8a8a8a on #fff ≈ 3.45 < 4.5）被判 FAIL", bool(lo)),
        ("对照臂：高对比度正文（#111111 on #fff ≈ 18.9）未被判 FAIL", not hi),
    ]
    print("== selftest（合成页；⛔ 不改站点）==")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    good = all(ok for _, ok in checks)
    print("  SELFTEST:", "PASS" if good else "FAIL（判据可能恒真或过判）")
    return 0 if good else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="双主题合成后对比度实测")
    ap.add_argument("--base", default=None,
                    help=f"站点基址（缺省 {DEFAULT_BASE}；亦可由 SITE_BASE 环境变量给出）")
    ap.add_argument("--selftest", action="store_true",
                    help="合成页负向夹具，验证判据非恒真（⛔ 不访问站点）")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    base = resolve_base(args.base)
    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in THEMES:
            print(f"\n=== {theme} ===")
            tertiary = TERTIARY_RGB[theme]
            for width in (1440, 390):
                ctx = browser.new_context(
                    viewport={"width": width, "height": 900}, reduced_motion="reduce"
                )
                # init script 在每个文档的页面脚本之前跑 ⇒ 首帧即为强制档，无需 reload
                ctx.add_init_script(f"localStorage.setItem('ui-theme','{theme}')")
                for path, label in PAGES:
                    page = ctx.new_page()
                    page.goto(f"{base}{path}", wait_until="networkidle")
                    page.wait_for_timeout(400)
                    worst, page_failures = probe_page(page, theme, tertiary, label, width)
                    page.close()
                    failures.extend(page_failures)
                    parts = []
                    for key, (c, bg, txt) in sorted(worst.items()):
                        th = NONBODY_MIN if key == "非正文" else BODY_MIN
                        parts.append(f"{key}={c:4.2f}{'OK' if c >= th else '!!'}(bg{bg})")
                    print(f"  {label} @{width}: " + (" · ".join(parts) if parts else "无样本"))
                ctx.close()
        browser.close()

    print(f"\n双主题合成后对比度（最坏情况）: {'ALL OK' if not failures else 'HAS FAILURE'}")
    for f in failures[:25]:
        print("  !!", f)
    print(f"  （失败 {len(failures)} 处）")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
