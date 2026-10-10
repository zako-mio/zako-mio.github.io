#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无障碍（a11y）自动化审查探针（批十五 B2）—— **axe-core 注入式**，⛔ 不引 Node 侧依赖。

为什么是「注入」而不是 axe-selenium：本仓浏览器层已有 **playwright**（`requirements-probes.txt`），
axe-core 是一个**纯前端 JS 库**（vendored 于 `scripts/probes/vendor/axe.min.js`，见其 README），
用 `page.add_script_tag()` 注入 + `axe.run()` 即可，⛔ 不必再引入 selenium/Node 工具链。

判据（读**站点真产物**；浏览器渲染后的可访问性树）：
    A1 **规则白名单**：只跑 `TAGS` 声明的规则集（WCAG 2.1/2.2 A/AA ＋ best-practice）
    A2 **违规 fail-closed**：任一未被 `EXCEPTIONS` 覆盖的 violation ⇒ rc=1
    A3 **豁免自证（self-retiring）**：`EXCEPTIONS` 里的每条豁免**必须真的命中**至少一处 ──
       命中不了 ⇒ FAIL（⛔ 防止「豁免静默过期」变成永久逃生门）
    A4 **非空守卫**：扫过的页数/注入是否成功必须可证；一页都没扫到 ⇒ rc=2（用法错误，⛔ 不当 PASS）

⚠ **必须先等过渡落定再跑 axe**（本批实测的坑，同批十四 b136）：
   `[data-reveal]` 的进场动画未走完时，元素处于**部分不透明度** ⇒ 合成色比真值浅，
   会被 axe 判成 `color-contrast` 不足（实测 `/about/#portrait .detail__note` 报 4.41，
   而落定后真值 `#5f6d84 on #f4f7fc` ≈ 4.88 ⇒ 合格）。**未落定就取样 = 假 FAIL**。

⚠ 声明的不覆盖面：
  ① 只判 axe 的 `violations`；⛔ 不判 `incomplete`（需人工复核项）。
  ② 色彩/对比是**渲染后**的合成结果，主题/宽度是最坏值抽样而非全量（双主题 × 定宽）。
  ③ ⛔ 不替代真机 + 屏幕阅读器实测。

用法：
    python3 scripts/probes/axe_a11y_probe.py [--base http://127.0.0.1:4399]
    python3 scripts/probes/axe_a11y_probe.py --selftest          # 合成夹具：对照臂 + 负向臂
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
AXE_JS = Path(__file__).resolve().parent / "vendor" / "axe.min.js"

# ── 规则白名单（判据 A1）────────────────────────────────────────────────────
# 规范层：WCAG 2.1 A/AA ＋ WCAG 2.2 AA。best-practice 层额外纳入，
# ★ 理由：本次实测暴露的 `heading-order`（/works h1→h3 跳级）属 best-practice 而非规范层 ——
#   恰恰是本站既有的对比度/几何/交互判据**都没在看**的一类 ⇒ 纳入它才有增量。
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]

# ── 路由（覆盖每种模板；★ 每个模板至少一条）──────────────────────────────────
ROUTES = [
    "/",                                  # 首页（Hero + 派生区块）
    "/works/",                            # 索引（卡片网格 + 筛选控件）
    "/stats/",                            # 聚合（图表 SVG + 表格 + 术语层）
    "/about/",                            # 关于（散文 + 联系）
    "/works/12-factor-methodology-kg/",   # 详情（图谱 + 关联）
]
THEMES = ["light", "dark"]                # 双主题（对比度在暗色下不同）

# ── 显式豁免（判据 A3：每条必须带 reason 且必须真命中，否则 FAIL）──────────────
EXCEPTIONS: list[dict] = []  # 现为空：全路由 × 双主题实测 0 违规

SETTLE_MS = 1600           # ≥ 最长有限过渡（--dur-4 0.85s）＋ 余量
RUN_JS = """async (tags) => {
  const r = await axe.run(document, {
    resultTypes: ['violations'],
    runOnly: { type: 'tag', values: tags },
  });
  return r.violations.map(v => ({
    id: v.id, impact: v.impact, help: v.help,
    nodes: v.nodes.map(n => ({ target: n.target.join(' '),
                               summary: (n.failureSummary || '').replace(/\\n/g, ' ') })),
  }));
}"""

FAILS: list[str] = []


def chk(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def settle(page) -> None:
    """触发所有 `[data-reveal]` 并等过渡落定（⛔ 不落定就取样会假 FAIL，见模块 docstring）。"""
    page.evaluate(
        "() => { const h = document.body.scrollHeight;"
        " for (let y = 0; y < h; y += 600) window.scrollTo(0, y);"
        " window.scrollTo(0, 0); }"
    )
    page.wait_for_timeout(SETTLE_MS)


def scan(page, base: str, route: str, theme: str) -> list[dict]:
    page.emulate_media(color_scheme=theme)
    page.goto(base + route, wait_until="load")
    settle(page)
    page.add_script_tag(path=str(AXE_JS))
    if page.evaluate("() => typeof axe") != "object":
        raise RuntimeError(f"axe 未注入成功（{theme} {route}）")
    return page.evaluate(RUN_JS, TAGS)


def covered(violation_id: str, target: str, exceptions: list[dict]) -> bool:
    return any(e["rule"] == violation_id and e["target"] in target for e in exceptions)


def report(base: str, exceptions: list[dict]) -> int:
    import urllib.request

    from playwright.sync_api import sync_playwright

    print(f"== a11y 探针（axe-core 注入）· {base} · 规则 {TAGS} ==")
    # 用法错误守卫（与 hover_gating 同口径）：静态服务未起 ⇒ rc=2，⛔ 不读成判据 FAIL。
    try:
        urllib.request.urlopen(base + ROUTES[0], timeout=5)
    except Exception as exc:  # noqa: BLE001
        print(f"  [用法错误] 站点不可达：{base}{ROUTES[0]}（{exc}）")
        print("  ⛔ 这不是判据 FAIL —— 先起静态服务："
              "setsid python3 -m http.server 4399 --directory out </dev/null & disown")
        return 2

    hits = {i: 0 for i in range(len(exceptions))}
    pages_scanned = 0
    violations: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for theme in THEMES:
            for route in ROUTES:
                for v in scan(page, base, route, theme):
                    for n in v["nodes"]:
                        if covered(v["id"], n["target"], exceptions):
                            for i, e in enumerate(exceptions):
                                if e["rule"] == v["id"] and e["target"] in n["target"]:
                                    hits[i] += 1
                            continue
                        violations.append(f"{theme} {route} · [{v['id']}/{v['impact']}] {n['target']} :: {n['summary'][:140]}")
                pages_scanned += 1
        browser.close()

    # A4 非空守卫（⛔ 判据不得哑火：真扫过的页数必须＝期望，否则是用法错误而非 PASS）
    expected = len(ROUTES) * len(THEMES)
    if not AXE_JS.exists():
        chk("A4 axe 脚本存在", False, str(AXE_JS))
        print("\nA11Y: USAGE ERROR（缺 vendored axe）")
        return 2
    if pages_scanned != expected:
        chk("A4 扫描非空", False, f"实际扫过 {pages_scanned} / 期望 {expected}")
        print("\nA11Y: USAGE ERROR（未按期望扫描；⛔ 不当 PASS）")
        return 2
    chk("A4 扫描非空", True, f"扫过 {pages_scanned} 页（{len(ROUTES)} 路由 × {len(THEMES)} 主题）")

    # A2 违规 fail-closed
    chk("A2 无未豁免违规（wcag A/AA ＋ best-practice）", not violations,
        f"违规 {len(violations)} 条" + ("" if not violations else "：\n      " + "\n      ".join(violations[:20])))

    # A3 豁免自证
    stale = [f"#{i} {e['rule']} target~{e['target']!r}（{e['reason']}）" for i, e in enumerate(exceptions) if hits[i] == 0]
    chk("A3 豁免全部真命中（⛔ 无静默过期豁免）", not stale, f"未命中 {len(stale)} 条" + (f"：{stale}" if stale else f"（共 {len(exceptions)} 条豁免）"))

    print("\nA11Y: " + ("ALL PASS" if not FAILS else f"FAIL {len(FAILS)} · {FAILS}"))
    return 1 if FAILS else 0


# ───────────────────────── selftest：合成夹具（对照臂 + 负向臂） ─────────────────────────

COMPLIANT = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>合规夹具</title></head><body>
<main><h1>页面标题</h1><h2>小节</h2><h3>子节</h3>
<p style="color:#0e1729"><a href="#x">链接文字</a></p></main></body></html>"""

# 负向夹具：同时注入三类违规（缺 alt / 标题跳级 / 低对比）
BROKEN = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>负向夹具</title></head><body>
<main><h1>标题</h1><h3>跳过了 h2</h3>
<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">
<p style="color:#bbbbbb;background:#ffffff">低对比正文，应被判 color-contrast。</p>
</main></body></html>"""


def _axe_on_html(html: str) -> list[dict]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(html, wait_until="load")
        pg.wait_for_timeout(150)
        pg.add_script_tag(path=str(AXE_JS))
        out = pg.evaluate(RUN_JS, TAGS)
        b.close()
    return out


def selftest() -> int:
    print("== selftest（合成夹具；⛔ 不写主报告）==")
    ok = True

    # 对照臂：合规夹具 ⇒ 0 违规（证明判据不是恒 FAIL）
    good = _axe_on_html(COMPLIANT)
    ok &= not good
    print(f"  [{'PASS' if not good else 'FAIL'}] 对照臂：合规夹具 0 违规" + ("" if not good else f" · {[v['id'] for v in good]}"))

    # 负向臂：注入违规 ⇒ 必须被抓到（证明判据能 FAIL，⛔ 不是哑火）
    bad = _axe_on_html(BROKEN)
    ids = {v["id"] for v in bad}
    wants = {"image-alt", "heading-order", "color-contrast"}
    hit = wants & ids
    ok &= len(hit) >= 2
    print(f"  [{'PASS' if len(hit) >= 2 else 'FAIL'}] 负向夹具：抓到违规 {sorted(ids)}（期望含 {sorted(wants)} 中 ≥2）")

    # 豁免自证的反向验证：把负向夹具的一处违规「豁免」掉 ⇒ 该例外必须被判「真命中」（不 stale）
    if bad:
        v0 = bad[0]
        tgt = v0["nodes"][0]["target"]
        ex = [{"rule": v0["id"], "target": tgt, "reason": "selftest 临时"}]
        c = covered(v0["id"], tgt, ex)
        ok &= c is True
        print(f"  [{'PASS' if c else 'FAIL'}] 豁免机制：精确 rule+target 能命中（避免 A3 误判过期）")

    print(f"\nSELFTEST: {'ALL PASS' if ok else 'HAS FAILURE'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="axe-core 注入式 a11y 探针")
    ap.add_argument("--base", default="http://127.0.0.1:4399")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    return report(args.base, EXCEPTIONS)


if __name__ == "__main__":
    sys.exit(main())
