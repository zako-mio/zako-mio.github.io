#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动效预算门控（批十一 §4-②）—— 进场/常驻动效的**失控守卫**。

为什么需要它：
  「动效预算」不是对比度/包体那样的**贴合式**阈值。本门控只做一件事 ——
  **数量级失控守卫**：防止某次改版静默引入「一页上百个进场元素」「错峰 3 秒」
  「常驻动画几十个」这类**总时长/总开销失控**。⛔ 它**不判**「动效好不好看」
  （观感归人），也不判「够不够」——与 `gate_ia_division` 的 A6/A9 棘轮同一取向。

★★ 阈值推导（**铁律：不得由规模直觉推导；必须先实测建基线，再乘既定余量**）
  `as_of=2026-10-09` · 站点 HEAD=`be457d8`+批十一改动 · 构建 17 页

  | id | 量（读法见下） | 基线最坏值 | 余量 | 阈值 |
  |---|---|---|---|---|
  | M1 | 单页 `[data-reveal]` 实例数（HTML **属性**计数） | 8（`/about`） | ×4 | ≤ 32 |
  | M2 | **进场完成时间** = 最大错峰（`--i×70ms`）＋ 最长 `--dur-*` | 990ms（140＋850） | 项目常量自导 | ≤ 兜底窗口 |
  | M3 | `--dur-*` 设计令牌之和 | 1.79s | ×2（上取 0.1s） | ≤ 3.6s |
  | M4 | 常驻（`infinite`）动画的**元素数**（CSS 选择器 → 产物计数） | 6（`/`） | ×2 | ≤ 12 |

  · M1 余量 ×4：页面正常增删 section（实测 `/about` 8 个）不会触发；只有数量级失控
    （几十 → 上百）才会。⛔ 贴合式阈值（如 ≤10）会把正常内容增长变成误报。
  · M2 的上界**由项目常量推导**（不是由基线推）：`MOTION_INIT_SCRIPT` 有一个
    **1800ms 兜底定时器**（运行时若未接管就把全部 `[data-reveal]` 一次摊平）⇒
    「进场动效应当在兜底触发前结束」是一条真实的机制约束，故取 `兜底窗口` 为上界
    （该数字**当场从 `src/lib/motion.ts` 解析**，⛔ 不写第二处字面量）。基线 990ms ⇒ 1.8 倍余量。
    ⚠ **作用面声明**：M2 只量**进场**类错峰（`--i` 来自数组下标，会随内容增长）；
    CSS 里另一族 `animation-delay`（流星 2.5/9/16s、漂移等**常驻环境**动画）**不是进场延迟**，
    只作报告项 ⇒ ⛔ 不得把它们并进 M2（首版判据正是这么错把 16s 流星当成「错峰」而假 FAIL）。
  · M3 余量 ×2：令牌之和＝「同时段内可叠加的动画时长总量」；×2 是失控守卫。
  · M4 余量 ×2：`infinite` 动画是**常驻**合成开销（与进场动画不同，它永远不结束），
    故单独设上界；基线 6（漂移照片×2 + 流星×3 + 首屏滚动提示×1）。
  · ⛔ 四项都是**上界**，任一项被突破即 FAIL；四项都在上界内**不等于**「动效预算合理」
    （那属观感裁决）。

读法与覆盖（与 `gate_background_salience.py` 的分工，⛔ 避免第二真相源）：
  · M1/M2/M4 读 `out/` 真实产物（M2 的时长令牌读源码 CSS，兜底窗口读 `src/lib/motion.ts`）；
    M3 读源码 CSS 的令牌。
  · `gate_background_salience.py` 的报告项给出「声明 animation 的背景选择器」清单（CSS 侧、
    含非 infinite）；本门控的 M4 数的是**产物里的常驻动画元素数**（页面侧、仅 infinite）
    ⇒ 两个对象不同、各自单一来源，⛔ 不互为副本。
  · 免责范围：本门控**不**度量真实帧率/掉帧/耗电（须真机，另见报告登记的未测项）。

用法：
    pnpm build && python3 scripts/gate_motion_budget.py     # ⛔ 读 out/ ⇒ 必须先构建
    python3 scripts/gate_motion_budget.py --selftest
退出码：0 = ALL PASS；1 = 有 FAIL；2 = 用法/解析错误（缺 out/ 时属此类，⛔ 不读成判据 FAIL）。
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "src/app/globals.css"
MOTION_TS = ROOT / "src/lib/motion.ts"
OUT_DIR = ROOT / "out"

# ── 阈值（推导见模块头注；⛔ 改阈值必须同时更新头注里的推导）──
M1_MAX_REVEAL = 32
M3_MAX_DUR_SUM_S = 3.6
M4_MAX_INFINITE_ELEMENTS = 12
FALLBACK_FALLBACK_MS = 1800  # 仅当 motion.ts 解析失败时用（会打 WARN）；⛔ 不作为常规真相源

STAGGER_STEP_MS = 70  # globals.css: animation-delay: calc(var(--i, 0) * 70ms)

# ⚠ `[data-reveal]` 也会出现在 pre-paint 内联脚本的字符串里（`querySelectorAll('[data-reveal]')`）
#   与 RSC Flight 载荷（`data-reveal\":true`）⇒ 必须限定「前面不是 `[`/词字符、后面是空白/`>`/`=`」。
REVEAL_ATTR = re.compile(r"(?<![\[\w-])data-reveal(?=[\s>=/])")
STAGGER_I = re.compile(r"--i:\s*(\d+)")
DUR_TOKEN = re.compile(r"--dur-(\d):\s*([0-9.]+)s")
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
# `animation-delay: Xs`（报告项）与 `animation:` 简写里的延迟值（报告项）
FIXED_DELAY = re.compile(r"animation-delay:\s*([0-9.]+)s")
SHORTHAND_DELAY = re.compile(r"animation:\s*[^;]*?\s([0-9.]+)s\s+(?:both|forwards|backwards|none)")
# MOTION_INIT_SCRIPT 的兜底定时器：`setTimeout(function(){…},1800);`
FALLBACK_TIMER = re.compile(r"setTimeout\([\s\S]*?,(\d+)\)")
CLASS_TOKEN = re.compile(r"\.([A-Za-z][A-Za-z0-9_-]*)")


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def read_fallback_ms() -> int:
    """当场从 `src/lib/motion.ts` 解析兜底窗口（⛔ 不写第二处字面量）。"""
    try:
        m = FALLBACK_TIMER.search(MOTION_TS.read_text(encoding="utf-8"))
    except OSError:
        m = None
    if not m:
        print(f"  [WARN] 无法从 {MOTION_TS.name} 解析兜底定时器 ⇒ 暂用 {FALLBACK_FALLBACK_MS}ms"
              "（判据依据漂移，请复核）")
        return FALLBACK_FALLBACK_MS
    return int(m.group(1))


def measure(css_path: Path, out_dir: Path) -> dict:
    """当场重算四项读数（⛔ 不复读任何历史记录）。"""
    css = strip_comments(css_path.read_text(encoding="utf-8"))

    durs = {m.group(1): float(m.group(2)) for m in DUR_TOKEN.finditer(css)}
    dur_sum = sum(durs.values())
    max_dur_ms = max(durs.values()) * 1000 if durs else 0.0

    # 报告项：CSS 里全部 animation-delay（含常驻环境动画）——⛔ 不并进 M2
    fixed_delays_ms = sorted({int(float(v) * 1000) for v in
                              FIXED_DELAY.findall(css) + SHORTHAND_DELAY.findall(css)})

    # M4：先由 CSS 推出「含 infinite 的规则」的类令牌，再在产物里数元素（不写死类名）
    infinite_tokens: set[str] = set()
    for sel, decl in RULE.findall(css):
        if "infinite" in decl:
            infinite_tokens |= set(CLASS_TOKEN.findall(sel))

    pages: list[dict] = []
    for page in sorted(out_dir.rglob("*.html")):
        html = page.read_text(encoding="utf-8", errors="replace")
        idx = [int(v) for v in STAGGER_I.findall(html)]
        n_inf = 0
        for token in infinite_tokens:
            n_inf += len(re.findall(r'class="[^"]*\b' + re.escape(token) + r'\b[^"]*"', html))
        pages.append({
            "page": str(page.relative_to(out_dir)),
            "reveal": len(REVEAL_ATTR.findall(html)),
            "stagger_ms": max(idx) * STAGGER_STEP_MS if idx else 0,
            "infinite": n_inf,
        })

    return {
        "durs": durs,
        "dur_sum_s": round(dur_sum, 3),
        "max_dur_ms": max_dur_ms,
        "fixed_delays_ms": fixed_delays_ms,
        "fallback_ms": read_fallback_ms(),
        "infinite_tokens": sorted(infinite_tokens),
        "pages": pages,
    }


def evaluate(m: dict) -> list[tuple[str, bool, str]]:
    pages = m["pages"]
    if not pages:
        return [("M0", False, "out/ 下没有 HTML 产物（先跑 pnpm build）")]

    worst_reveal = max(pages, key=lambda p: p["reveal"])
    worst_inf = max(pages, key=lambda p: p["infinite"])
    max_stagger = max(p["stagger_ms"] for p in pages)
    enter_ms = max_stagger + m["max_dur_ms"]

    return [
        ("M1", worst_reveal["reveal"] <= M1_MAX_REVEAL,
         f"单页 [data-reveal] 最多 {worst_reveal['reveal']} 个（{worst_reveal['page']}；上界 {M1_MAX_REVEAL}）"),
        ("M2", enter_ms <= m["fallback_ms"],
         f"进场完成时间 {enter_ms:.0f}ms（错峰 {max_stagger}ms ＋ 最长时长 {m['max_dur_ms']:.0f}ms）"
         f" ≤ 兜底窗口 {m['fallback_ms']}ms"),
        ("M3", m["dur_sum_s"] <= M3_MAX_DUR_SUM_S,
         f"--dur-* 之和 {m['dur_sum_s']}s {m['durs']}（上界 {M3_MAX_DUR_SUM_S}s）"),
        ("M4", worst_inf["infinite"] <= M4_MAX_INFINITE_ELEMENTS,
         f"单页常驻(infinite)动画元素最多 {worst_inf['infinite']} 个（{worst_inf['page']}；"
         f"类令牌 {m['infinite_tokens']}；上界 {M4_MAX_INFINITE_ELEMENTS}）"),
    ]


def run(css_path: Path, out_dir: Path) -> tuple[bool, list[str]]:
    print("== 动效预算门控（四项上界；读源码 CSS ＋ out/ 真实产物）==")
    m = measure(css_path, out_dir)
    results = evaluate(m)
    for cid, passed, detail in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {cid}  {detail}")
    print("\n  · 逐页读数：")
    for p in m["pages"]:
        print(f"      {p['page']:<44} reveal={p['reveal']:<3} 错峰={p['stagger_ms']:<4}ms 常驻={p['infinite']}")
    print(f"\n  · 报告项（⛔ 不判）：CSS 中全部 animation-delay（含常驻环境动画）="
          f"{m['fixed_delays_ms']}ms  ← 其中仅错峰进 M2；流星/漂移属常驻环境延迟，不是进场延迟")
    print("  ⚠ 声明的不判面：本门控⛔ 不度量真实帧率/掉帧/耗电（须真机）；"
          "四项在上界内 ⛔ 不等于「动效观感合理」（属裁决）。")
    ok = all(passed for _, passed, _ in results)
    findings = [f"{cid} {detail}" for cid, passed, detail in results if not passed]
    print("\nMOTION BUDGET:", "ALL PASS" if ok else "HAS FAILURE")
    return ok, findings


# ───────────────────────────── 负向夹具 ─────────────────────────────

FIXTURE_CSS = """
:root { --dur-1: 0.16s; --dur-2: 0.28s; --dur-3: 0.5s; --dur-4: 0.85s; }
html.js-motion [data-reveal].is-in {
  animation: reveal-in var(--dur-4) var(--ease-out) both;
  animation-delay: calc(var(--i, 0) * 70ms);
}
html.js-motion .hero__inner > *:nth-child(2) { animation-delay: 0.06s; }
html.js-motion .hero__map { animation: rise-in var(--dur-4) var(--ease-out) 0.24s both; }
.backdrop__photo { animation: drift 160s linear infinite alternate; }
.backdrop__meteor { animation-iteration-count: infinite; }
.hero__cue-dot { animation: cue-drop 2.4s linear infinite; }
"""
FIXTURE_HTML = (
    '<html><body>'
    '<span class="backdrop__photo backdrop__photo--night"></span>'
    '<span class="backdrop__photo backdrop__photo--day"></span>'
    '<i class="backdrop__meteor backdrop__meteor--1"></i>'
    '<i class="backdrop__meteor backdrop__meteor--2"></i>'
    '<i class="backdrop__meteor backdrop__meteor--3"></i>'
    '<span class="hero__cue-dot"></span>'
    + "".join(f'<section data-reveal style="--i:{i}">s{i}</section>' for i in range(3))
    + "<script>document.querySelectorAll('[data-reveal]');</script>"
    + "</body></html>"
)


def selftest() -> int:
    cases: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        def fixture(name: str, css: str, html: str):
            d = tmp / name
            (d / "out").mkdir(parents=True, exist_ok=True)
            (d / "globals.css").write_text(css, encoding="utf-8")
            (d / "out" / "index.html").write_text(html, encoding="utf-8")
            return d / "globals.css", d / "out"

        ok, _ = run(*fixture("base", FIXTURE_CSS, FIXTURE_HTML))
        cases.append(("对照臂：合规基线（期望 PASS）", ok))

        # 负向夹具 1：单页进场元素数量级失控（M1）
        blowup = FIXTURE_HTML.replace("</body>", "".join(
            f'<i data-reveal style="--i:{i}"></i>' for i in range(40)) + "</body>")
        ok, _ = run(*fixture("m1", FIXTURE_CSS, blowup))
        cases.append(("负向夹具1：单页 43 个 [data-reveal] 被抓到（期望 FAIL）", not ok))

        # 负向夹具 2：错峰延迟超一个 --dur-4（M2）
        slow = FIXTURE_HTML.replace("--i:2", "--i:16")
        ok, _ = run(*fixture("m2", FIXTURE_CSS, slow))
        cases.append(("负向夹具2：错峰 16×70ms=1120ms 被抓到（期望 FAIL）", not ok))

        # 负向夹具 3：新增超长时长令牌（M3）
        long_dur = FIXTURE_CSS.replace("--dur-4: 0.85s;", "--dur-4: 3.2s;")
        ok, _ = run(*fixture("m3", long_dur, FIXTURE_HTML))
        cases.append(("负向夹具3：令牌之和 4.14s 被抓到（期望 FAIL）", not ok))

        # 负向夹具 4：常驻动画元素数量翻倍（M4）
        many_inf = FIXTURE_CSS + "\n.drift-extra { animation: x 5s linear infinite; }\n"
        many_html = FIXTURE_HTML.replace("</body>", "".join(
            '<u class="drift-extra"></u>' for _ in range(8)) + "</body>")
        ok, _ = run(*fixture("m4", many_inf, many_html))
        cases.append(("负向夹具4：常驻动画元素 14 个 被抓到（期望 FAIL）", not ok))

    print("\n== selftest ==")
    for name, passed in cases:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    all_ok = all(p for _, p in cases)
    print("  SELFTEST:", "PASS" if all_ok else "FAIL（判据可能恒真或恒假）")
    return 0 if all_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="动效预算门控（四项上界）")
    ap.add_argument("--selftest", action="store_true", help="跑负向夹具（含期望 FAIL 的样本）")
    ap.add_argument("--css", type=Path, default=CSS_PATH)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.css.exists():
        print(f"[用法错误] 找不到 {args.css}")
        return 2
    if not args.out.exists():
        print("[用法错误] out/ 不存在 —— 本门控读真实产物，请先 pnpm build")
        return 2
    ok, _ = run(args.css, args.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
