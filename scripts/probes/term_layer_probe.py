#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""术语解释层探针（第十四批 W2）。

判据（读**站点真产物**；单一真相源＝`src/data/glossary.json`，本探针只测**呈现与交互**）：
    T1 静止态隐藏          `.term__def` 在无 hover/focus 时 `display:none`（⛔ 不是「常显」）
    T2 hover 展开          hover 触发器 ⇒ 面板可见且有实际盒子
    T3 键盘 focus 展开     `.focus()` ⇒ 面板可见（WCAG 1.4.13：有 hover 就必须有焦点等价）
    T4 Esc 关闭            Esc ⇒ 面板收起（WAI-ARIA tooltip 模式）
    T5 语义关联            `aria-describedby` 指向**存在**且 `role="tooltip"` 的节点
    T6 无 JS 可读          原始 HTML（⛔ 不经浏览器/JS）里已含定义文本 ⇒ 渐进增强的「底」

用法：
    python3 term_layer_probe.py [--base http://127.0.0.1:4399] [--path /stats/]
    python3 term_layer_probe.py --selftest        # 合成夹具逐例变异（⛔ 不写主报告）
"""
from __future__ import annotations

import argparse
import sys
import urllib.request

from no_js_readable import raw_html_has_definition  # 共享实现（单一真相源，见该模块 docstring）

sys.stdout.reconfigure(encoding="utf-8")

FAILS: list[str] = []


def chk(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


# ───────────────────────── T1–T5：浏览器行为 ─────────────────────────

STATE_JS = """(sel) => {
  const t = document.querySelector(sel);
  if (!t) return { missing: true };
  const wrap = t.closest('.term') || t.parentElement;
  const def = wrap ? wrap.querySelector('.term__def') : null;
  if (!def) return { noDef: true };
  const cs = getComputedStyle(def);
  const r = def.getBoundingClientRect();
  const id = t.getAttribute('aria-describedby');
  const target = id ? document.getElementById(id) : null;
  return {
    display: cs.display, w: Math.round(r.width), h: Math.round(r.height),
    describedby: id,
    role: def.getAttribute('role'),
    linkOk: !!target && target === def,
    text: (def.textContent || '').trim(),
  };
}"""


def probe_page(pg, check: dict | None = None) -> dict:
    """对当前页跑 T1–T5，返回 [{name, ok, detail}]。"""
    sel = ".term__trigger"
    out: list[dict] = []
    base = pg.evaluate(STATE_JS, sel)
    ok1 = isinstance(base, dict) and not base.get("missing") and not base.get("noDef") and base.get("display") == "none"
    out.append({"name": "T1 静止态隐藏", "ok": bool(ok1), "detail": f"display={base.get('display') if isinstance(base, dict) else base}"})

    ok5 = bool(isinstance(base, dict) and base.get("role") == "tooltip" and base.get("linkOk"))
    out.append({"name": "T5 语义关联（aria-describedby→role=tooltip）", "ok": ok5,
                "detail": f"describedby={base.get('describedby') if isinstance(base,dict) else ''} role={base.get('role') if isinstance(base,dict) else ''} 可达={base.get('linkOk') if isinstance(base,dict) else ''}"})

    el = pg.query_selector(sel)
    if el is None:
        out.append({"name": "T2 hover 展开", "ok": False, "detail": "无触发器"})
        out.append({"name": "T3 键盘 focus 展开", "ok": False, "detail": "无触发器"})
        out.append({"name": "T4 Esc 关闭", "ok": False, "detail": "无触发器"})
        return out

    el.scroll_into_view_if_needed()
    pg.wait_for_timeout(150)
    box = el.bounding_box()
    pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    pg.wait_for_timeout(250)
    hot = pg.evaluate(STATE_JS, sel)
    ok2 = isinstance(hot, dict) and hot.get("display") == "block" and (hot.get("h") or 0) > 10
    out.append({"name": "T2 hover 展开", "ok": bool(ok2), "detail": f"display={hot.get('display') if isinstance(hot,dict) else hot} {hot.get('w') if isinstance(hot,dict) else ''}x{hot.get('h') if isinstance(hot,dict) else ''}"})

    pg.mouse.move(4, 4)
    pg.wait_for_timeout(200)
    pg.evaluate("(s) => document.querySelector(s).focus()", sel)
    pg.wait_for_timeout(200)
    foc = pg.evaluate(STATE_JS, sel)
    out.append({"name": "T3 键盘 focus 展开", "ok": bool(isinstance(foc, dict) and foc.get("display") == "block"),
                "detail": f"display={foc.get('display') if isinstance(foc,dict) else foc}"})

    pg.keyboard.press("Escape")
    pg.wait_for_timeout(250)
    esc = pg.evaluate(STATE_JS, sel)
    out.append({"name": "T4 Esc 关闭", "ok": bool(isinstance(esc, dict) and esc.get("display") == "none"),
                "detail": f"display={esc.get('display') if isinstance(esc,dict) else esc}"})
    return out


def run_site(base: str, path: str) -> int:
    from playwright.sync_api import sync_playwright

    print(f"== 术语解释层探针（{base}{path}）==")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(base + path, wait_until="load")
        pg.wait_for_timeout(400)
        for r in probe_page(pg):
            chk(r["name"], r["ok"], r["detail"])
        b.close()

    html = urllib.request.urlopen(base + path, timeout=30).read().decode("utf-8", "replace")
    chk("T6 无 JS 可读（原始 HTML 已含定义）", raw_html_has_definition(html),
        f"含非空 .term__def 面板={raw_html_has_definition(html)}")

    print("\nTERM-LAYER: " + ("ALL PASS" if not FAILS else f"FAIL {len(FAILS)} · {FAILS}"))
    return 1 if FAILS else 0


# ───────────────────────── selftest（合成夹具，逐例变异） ─────────────────────────

FIXTURE_STYLE = """
<style>
.term { position: relative; display: inline; }
.term__trigger { appearance: none; background: none; border: 0; font: inherit; color: inherit; cursor: help; }
.term__def { position: absolute; display: none; width: 200px; padding: 8px; background: #fff; }
.term__trigger:hover { color: red; }
.term:hover .term__def { display: block; }
.term:focus-within .term__def { display: block; }
</style>
"""

FIXTURE_ESC_JS = """
<script>
window.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  const a = document.activeElement;
  const term = a && a.closest ? a.closest('.term') : null;
  if (!term) return;
  term.setAttribute('data-term-closed', '');
  if (a && a.blur) a.blur();
});
</script>
"""


def _fixture(def_attrs: str = 'id="g1" role="tooltip"', describedby: str = 'aria-describedby="g1"',
             def_text: str = "图论分层（最长路径）：把图按依赖关系一层层排开后，最长那条依赖链的层数。",
             with_esc: bool = True, closed_css: bool = True) -> str:
    esc = FIXTURE_ESC_JS if with_esc else ""
    closed = ".term[data-term-closed] .term__def { display: none; }" if closed_css else ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>" + FIXTURE_STYLE.replace(
            "</style>", closed + "</style>") + "</head><body>" + esc +
        f'<span class="term"><button type="button" class="term__trigger" {describedby}>拓扑层</button>'
        f'<span class="term__def" {def_attrs}>{def_text}</span></span>'
        "</body></html>"
    )


def selftest() -> int:
    from playwright.sync_api import sync_playwright

    print("== selftest（合成夹具；⛔ 不写主报告）==")
    ok = True

    def run_fixture(html: str) -> list[dict]:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 900, "height": 600})
            pg.set_content(html, wait_until="load")
            pg.wait_for_timeout(150)
            res = probe_page(pg)
            b.close()
        return res

    def verdict(res, name):
        return next((r["ok"] for r in res if r["name"] == name), None)

    # 对照臂：合规夹具 ⇒ T1–T5 全真（证明判据不是恒 FAIL）
    good = run_fixture(_fixture())
    control = all(r["ok"] for r in good)
    ok &= control
    print(f"  [{'PASS' if control else 'FAIL'}] 对照臂：合规夹具 T1–T5 全 PASS"
          + ("" if control else f" · {[r for r in good if not r['ok']]}"))

    # 负向 1：面板缺 role=tooltip ⇒ T5 必须 FAIL
    v = verdict(run_fixture(_fixture(def_attrs='id="g1"')), "T5 语义关联（aria-describedby→role=tooltip）")
    ok &= v is False
    print(f"  [{'PASS' if v is False else 'FAIL'}] 负向夹具 T5：缺 role=tooltip ⇒ 判 FAIL")

    # 负向 2：缺 aria-describedby ⇒ T5 必须 FAIL
    v = verdict(run_fixture(_fixture(describedby="")), "T5 语义关联（aria-describedby→role=tooltip）")
    ok &= v is False
    print(f"  [{'PASS' if v is False else 'FAIL'}] 负向夹具 T5：缺 aria-describedby ⇒ 判 FAIL")

    # 负向 3：去掉 Esc 处理 ⇒ T4 必须 FAIL
    v = verdict(run_fixture(_fixture(with_esc=False, closed_css=False)), "T4 Esc 关闭")
    ok &= v is False
    print(f"  [{'PASS' if v is False else 'FAIL'}] 负向夹具 T4：无 Esc 处理 ⇒ 判 FAIL")

    # 负向 4：面板常显（无 `display:none`）⇒ T1 必须 FAIL
    always = _fixture().replace(".term__def { position: absolute; display: none;",
                                ".term__def { position: absolute; display: block;")
    v = verdict(run_fixture(always), "T1 静止态隐藏")
    ok &= v is False
    print(f"  [{'PASS' if v is False else 'FAIL'}] 负向夹具 T1：面板常显 ⇒ 判 FAIL")

    # T6 的两个臂（纯字符串，无浏览器）
    pos = raw_html_has_definition(
        '<span class="term__def" id="x"><span class="term__body">图论分层（最长路径）：把图按依赖关系一层层排开的层数。</span></span>')
    neg_empty = raw_html_has_definition(
        '<span class="term__def" id="x"><span class="term__body"></span></span>')
    neg_missing = raw_html_has_definition('<div>页面里根本没有术语面板</div>')
    ok &= pos is True and neg_empty is False and neg_missing is False
    print(f"  [{'PASS' if pos and not neg_empty and not neg_missing else 'FAIL'}] "
          "T6 三臂：非空定义 ⇒ PASS / 空定义 ⇒ FAIL / 无面板 ⇒ FAIL")

    print(f"\nSELFTEST: {'ALL PASS' if ok else 'HAS FAILURE'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:4399")
    ap.add_argument("--path", default="/stats/")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    return run_site(args.base, args.path)


if __name__ == "__main__":
    sys.exit(main())
