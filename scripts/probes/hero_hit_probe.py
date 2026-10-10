#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hero 交互保护探针（第十三批 W1 验收项）。

为什么需要它（**这条判据的存在理由**）：
    批十三 W1 把 `.hero__map` 从 `<svg>` 改为 HTML wrapper 以承接指针高光。
    原 `.hero__map` 带 `pointer-events: none`，指针**根本命中不到它**；
    改造后 wrapper 参与命中测试 ⇒ **结构上多了一个可能遮挡 Hero 内可交互件的大面**。
    而 Hero 里有两个可点目标（主 CTA `a.button--primary` 与页内锚点 `a.hero__cue`）。
    ⛔ 这条风险**不能靠推断**（「正文列已由 `--hero-map-w` 让位、且图件 <1024px 隐藏」只是预期），
    必须有可复跑的机检 —— 否则将来任何一次布局/定位改动都可能静默把 CTA 变成点不动。

判据（H1–H4；行为口径，用 `document.elementFromPoint` 真实命中测试）：
    H1 逐目标命中：`.hero` 内每个可交互件的**几何中心**被 `elementFromPoint` 命中时，
                   必须解析回它自身或其后代（⛔ 被遮挡即 FAIL）。
    H2 不叠热区：`.hero__map` 的 bounding rect **不得**包含任何可交互件的中心
                   （即图件不得压在可点目标上）。
                   ★ 批十七（W4-②）**收窄了作用面**：图件**内部**的交互件（定位图的三个
                   方向链接）**不算**「被图件压住」—— 它们就是图件的一部分；判据面必须＝被判对象。
                   ⛔ 收窄**不是**放行：那三件仍逐件受 H1 管（中心必须命中回自己），
                   这正是本批新增交互的唯一保护，故本次改动净增了被检对象。
    H3 断点一致：视口 < 1024px ⇒ `.hero__map` 必须不可见（零尺寸或 display:none）；
                   ≥ 1024px ⇒ 必须可见。（断点口径与 globals.css 的 `max-width: 1023px` 同源）
    H4 可被命中：图件可见时，其自身中心必须能被命中到**它自己**（否则 W1 的
                   「指针跟随高光」拿不到 `pointermove` ⇒ 特效在 Hero 上是哑火的）。

⛔ 不覆盖面：本探针只判**遮挡/命中**，不判观感（光斑强弱、是否好看）。
    那属观感类，须人看对比件后裁决。

用法：
    setsid python3 -m http.server 4399 --directory out >/tmp/…log 2>&1 </dev/null & disown
    python3 scripts/probes/hero_hit_probe.py --out <留档目录>
    python3 scripts/probes/hero_hit_probe.py --out <留档目录> --selftest   # 合成夹具，验证判据非恒真
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_BASE = "http://127.0.0.1:4399"
BIG = {"width": 1440, "height": 900}      # 图件可见
EDGE = {"width": 1024, "height": 900}     # 断点上沿（图件仍应可见）
SMALL = {"width": 1023, "height": 900}    # 断点下沿（图件应不可见）

# （路径, 视口, 期望图件可见?）
RUNS: list[tuple[str, dict, bool]] = [
    ("/", BIG, True),
    ("/", EDGE, True),
    ("/", SMALL, False),
    ("/", {"width": 390, "height": 844}, False),
]

INTERACTIVE = 'a, button, [role="button"], summary, input, select, textarea'

AUDIT_JS = r"""
() => {
  const hero = document.querySelector('.hero');
  if (!hero) return { error: 'no .hero' };
  const sel = 'a, button, [role="button"], summary, input, select, textarea';
  const cls = (el) => (typeof el.className === 'string' ? el.className.trim().split(/\s+/).join('.') : '');
  const map = document.querySelector('.hero__map');
  const ms = map ? getComputedStyle(map) : null;
  const mb = map ? map.getBoundingClientRect() : null;
  const mapVisible = !!map && mb.width > 1 && mb.height > 1 && ms.display !== 'none';

  const targets = [...hero.querySelectorAll(sel)].map((el) => {
    const b = el.getBoundingClientRect();
    const cx = b.x + b.width / 2, cy = b.y + b.height / 2;
    const hit = document.elementFromPoint(cx, cy);
    const insideMap = mapVisible
      ? (cx >= mb.x && cx <= mb.x + mb.width && cy >= mb.y && cy <= mb.y + mb.height)
      : false;
    return {
      tag: el.tagName.toLowerCase(), cls: cls(el),
      text: (el.textContent || '').trim().slice(0, 24),
      size: [Math.round(b.width), Math.round(b.height)],
      center: [Math.round(cx), Math.round(cy)],
      hitBy: hit ? hit.tagName.toLowerCase() + '.' + cls(hit) : null,
      ok: !!hit && (hit === el || el.contains(hit)),
      insideMap,
      // ★ 批十七 W4-②：图件**内部**的交互件（定位图的三个方向链接）。
      //   ⛔ 它们不被 H2 判「被图件压住」—— 它们**就是**图件的一部分；
      //   但 H1 仍逐件判它们能否被命中（那正是本批新加交互的**唯一**保护）。
      isMapDescendant: !!(map && map.contains(el)),
      // ★ 批十七 W4-②：**零尺寸＝未渲染**。本探针在 <1024px 档也要跑（H3 断点一致），
      //   而该档 `.hero__map` 是 `display:none` ⇒ 图内链接 rect 为 0×0、中心落在 (0,0)，
      //   会被 `elementFromPoint` 命中外层容器而误判「遮挡」。
      //   ⇒ H1 只判**已渲染**的交互件（零尺寸者不是「被遮挡」，是**不存在**）。
      //   ⚠ 与 `surface_hit_probe` 同口径（它同样 `width<1||height<1` 即跳过）。
      zero: b.width < 1 || b.height < 1,
    };
  });

  let mapSelfHit = null;
  if (mapVisible) {
    const mcx = mb.x + mb.width / 2, mcy = mb.y + mb.height / 2;
    const mh = document.elementFromPoint(mcx, mcy);
    mapSelfHit = !!mh && (mh === map || map.contains(mh));
  }

  return {
    targets,
    map: map ? {
      size: [Math.round(mb.width), Math.round(mb.height)],
      display: ms.display, pointerEvents: ms.pointerEvents,
      visible: mapVisible, selfHit: mapSelfHit,
    } : null,
  };
}
"""


# ---------------------------------------------------------------- 夹具（负向）

SELFTEST_JS = r"""
(kind) => {
  // 在 Hero 内第一个可交互件上盖一层满覆盖遮罩 ⇒ H1 应被抓到
  const hero = document.querySelector('.hero');
  const t = hero && hero.querySelector('a, button, summary');
  if (!t) return { error: 'no target in hero' };
  const prev = document.getElementById('__st_cover');
  if (prev) prev.remove();
  if (kind === 'cover') {
    const b = t.getBoundingClientRect();
    const d = document.createElement('div');
    d.id = '__st_cover';
    d.style.cssText = `position:fixed;left:${b.x - 20}px;top:${b.y - 20}px;`
      + `width:${b.width + 40}px;height:${b.height + 40}px;z-index:99999;background:rgba(0,0,0,.01);`;
    document.body.appendChild(d);
  }
  return { ok: true };
}
"""


def audit(page) -> dict:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(250)          # 让 hydration 落定
    return page.evaluate(AUDIT_JS)


def judge(res: dict, expect_visible: bool) -> list[str]:
    """返回 FAIL 说明列表（空 = 该轮通过）。"""
    bad: list[str] = []
    if res.get("error"):
        return [f"页面结构异常：{res['error']}"]
    m = res.get("map")
    if m is None:
        return ["找不到 `.hero__map`（W1 的宿主约定缺失）"]

    # H1 逐目标命中（★ 批十七：零尺寸＝未渲染 ⇒ 不进作用面；见 AUDIT_JS 的 `zero` 注释）
    h1_skipped = 0
    for t in res["targets"]:
        if t.get("zero"):
            h1_skipped += 1
            continue
        if not t["ok"]:
            bad.append(f"H1 遮挡：`{t['tag']}.{t['cls']}`「{t['text']}」中心 {t['center']} "
                       f"被 `{t['hitBy']}` 命中")
    if h1_skipped:
        print(f"  ⓘ H1 跳过零尺寸（未渲染）可交互件 {h1_skipped} 个")
    # H2 不叠热区（★ 批十七收窄：⛔ 不把「图件内部的交互件」算作「被图件压住」）
    for t in res["targets"]:
        if t["insideMap"] and not t.get("isMapDescendant"):
            bad.append(f"H2 叠热区：`.hero__map` 覆盖了 `{t['tag']}.{t['cls']}`「{t['text']}」的中心")
    # H3 断点一致
    if m["visible"] != expect_visible:
        bad.append(f"H3 断点不一致：期望图件可见={expect_visible}，实得 visible={m['visible']}"
                   f"（display={m['display']} size={m['size']}）")
    # H4 可被命中（仅在图件可见时才有意义；此时它必须是「可被指针命中」的）
    if expect_visible and m["visible"] and m["selfHit"] is not True:
        bad.append(f"H4 哑火：图件可见但其中心命中的不是它自己（pointerEvents={m['pointerEvents']}）"
                   f" ⇒ 指针高光在 Hero 上取不到 pointermove")
    return bad


def selftest(page) -> list[dict]:
    page.goto(page.url, wait_until="networkidle") if page.url else None
    checks: list[dict] = []

    base = audit(page)
    base_bad = judge(base, True)
    h1_base = not any(b.startswith("H1") for b in base_bad)

    page.evaluate(SELFTEST_JS, "cover")
    page.wait_for_timeout(100)
    covered = audit(page)
    h1_covered = any(b.startswith("H1") for b in judge(covered, True))
    checks.append({
        "case": "负向夹具：给 Hero 首个可交互件盖满覆盖遮罩",
        "expected": "H1 应判遮挡（FAIL）",
        "got": "判遮挡" if h1_covered else "未判遮挡",
        "ok": h1_covered,
    })

    page.evaluate(SELFTEST_JS, "clear")
    page.wait_for_timeout(100)
    cleared = audit(page)
    h1_clear = not any(b.startswith("H1") for b in judge(cleared, True))
    checks.append({
        "case": "对照臂：移除遮罩后恢复",
        "expected": "H1 应不再判遮挡",
        "got": "无遮挡" if h1_clear else "仍判遮挡",
        "ok": h1_clear,
    })
    checks.append({
        "case": "前置守卫：未注入时本页 H1 本就干净",
        "expected": "H1 干净（否则夹具无法区分）",
        "got": "干净" if h1_base else "本已遮挡",
        "ok": h1_base,
    })
    return checks


def resolve_base(cli_base: str | None) -> str:
    return cli_base or os.environ.get("SITE_BASE") or DEFAULT_BASE


def main() -> int:
    ap = argparse.ArgumentParser(description="Hero 交互保护探针（W1 验收）")
    ap.add_argument("--out", required=True, type=Path, help="报告落盘目录（⛔ 不写仓库）")
    ap.add_argument("--base", default=None,
                    help=f"站点基址（缺省 {DEFAULT_BASE}；亦可由 SITE_BASE 环境变量给出）")
    ap.add_argument("--selftest", action="store_true", help="注入合成夹具验证判据非恒真（不写主报告）")
    args = ap.parse_args()
    base = resolve_base(args.base)
    args.out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        if args.selftest:
            page = browser.new_page(viewport=BIG)
            page.goto(base + "/", wait_until="networkidle")
            checks = selftest(page)
            page.close()
            browser.close()
            print("== selftest（合成夹具；⛔ 不写主报告）==")
            for c in checks:
                print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['case']}｜期望 {c['expected']}｜实得 {c['got']}")
            ok = all(c["ok"] for c in checks)
            print("  SELFTEST:", "PASS" if ok else "FAIL（判据可能恒真）")
            return 0 if ok else 1

        report: dict = {"base": base, "runs": []}
        bad: list[str] = []
        for path, viewport, expect_visible in RUNS:
            page = browser.new_page(viewport=viewport)
            page.goto(base + path, wait_until="networkidle")
            res = audit(page)
            page.close()
            label = f"{path} · {viewport['width']}px"
            fails = judge(res, expect_visible)
            report["runs"].append({"label": label, "expectMapVisible": expect_visible,
                                   "result": res, "failures": fails})
            print(f"== {label} ==  （期望图件可见={expect_visible}）")
            m = res.get("map") or {}
            print(f"   图件：visible={m.get('visible')} size={m.get('size')} "
                  f"display={m.get('display')} pointer-events={m.get('pointerEvents')} "
                  f"selfHit={m.get('selfHit')}")
            for t in res.get("targets", []):
                # ★ 批十七：零尺寸（未渲染，如 <1024px 档被 display:none 的图内链接）标「· 」
                #   —— ⛔ 不是「遮挡」，不该在报告里显示为失败标记（免得人误读）。
                flag = "·  " if t.get("zero") else ("OK " if t["ok"] else "⛔ ")
                print(f"   {flag}{t['tag']}.{t['cls']}「{t['text']}」size={t['size']} "
                      f"center={t['center']} ← {t['hitBy']}")
            for f in fails:
                print(f"   [FAIL] {f}")
                bad.append(f"[{label}] {f}")
            if not fails:
                print("   [PASS] H1–H4 全通过")

        browser.close()

    report["failures"] = bad
    report["result"] = "ALL PASS" if not bad else f"HAS FAILURE（{len(bad)}）"
    (args.out / "hero-hit-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Hero 交互保护探针（W1）", "",
             f"- 基址 {base} · 视口 {[r['label'] for r in report['runs']]}",
             "- 口径：`document.elementFromPoint` 真实命中测试（⛔ 不用 getBoundingClientRect 推断）。",
             "- H1 逐目标命中 · H2 不叠热区 · H3 断点一致 · H4 图件可被命中。", ""]
    for run in report["runs"]:
        m = run["result"].get("map") or {}
        lines += [f"## {run['label']}", "",
                  f"- `.hero__map`：visible={m.get('visible')} size={m.get('size')} "
                  f"pointer-events={m.get('pointerEvents')} selfHit={m.get('selfHit')}", "",
                  "| 目标 | 尺寸 | 中心 | 实际命中 | 判定 |", "|---|---|---|---|---|"]
        for t in run["result"].get("targets", []):
            lines.append(f"| `{t['tag']}.{t['cls']}`「{t['text']}」 | {t['size']} | {t['center']} | "
                         f"`{t['hitBy']}` | {'OK' if t['ok'] else '**遮挡**'} |")
        lines.append("")
        lines += [f"结论：{'ALL PASS' if not run['failures'] else ' · '.join(run['failures'])}", ""]
    (args.out / "hero-hit-report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\nHERO HIT: {report['result']}")
    print(f"[written] {args.out / 'hero-hit-report.json'} + hero-hit-report.md")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
