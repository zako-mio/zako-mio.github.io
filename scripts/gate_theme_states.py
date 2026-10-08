#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门控：主题三态与「双模 SVG 图表」的同步（B7）。

## 为什么需要它（问题陈述）

`/stats` 的图表由**两份**构建期生成的 SVG 组成：浅色帧（`.chart__frame`，默认显示）
与深色帧（`.chart__frame--dark`，默认 `display:none`）。哪一份显示**不由 JS 决定**，
而由 `src/app/globals.css` 的三段 CSS 决定（⛔ 不用 `light-dark()`，见 STACK-NOTES）：

  1. 强制深色：`[data-theme='dark'] .chart__frame--dark { display:block }` ＋ 隐藏浅色帧
  2. 强制浅色：`[data-theme='light'] .chart__frame--dark { display:none }`
  3. 跟随系统：`@media (prefers-color-scheme: dark) { :root:not([data-theme='light']) … }`

⇒ **若新增一个主题档**（改 `THEME_MODES`）或改选择器而**未同步这些规则**，
图表会**静默**停在错误的一份上（页面不报错、对比度门控也不管图表内容），无人察觉。
本门控把该同步关系固化为可复跑判据。

| id | 判据 | 依据 |
|---|------|------|
| T1 | `THEME_MODES` 的每个**强制档**（非 system）在 globals.css 中都有作用于 `.chart__frame` 的 `[data-theme='<档>']` 规则 | 新增档 ⇒ 必须同步显隐规则 |
| T2 | globals.css 含 `@media (prefers-color-scheme: dark)` 块，且块内作用于 `.chart__frame` 的规则 ≥1，并以 `:root:not([data-theme='light'])` 限定 | 「跟随系统」档的载体；限定条件防与强制浅色档互斥失效 |
| T3 | `.chart__frame--dark` 的**默认** `display:none` 规则存在 | 否则首帧两份 SVG 同时渲染 |
| T4 | `src/data/charts.json` 每张图的 `svg.light` 与 `svg.dark` 均非空 | 双模是**成对**契约 |
| T5 | 构建产物中凡出现 `.chart__frame` 的页面，其 `--dark` 实例数与浅色实例数相等且 ≥1 | 产物级成对（⛔ 不看源码自述） |

用法：
    python3 scripts/gate_theme_states.py
    python3 scripts/gate_theme_states.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

THEME_TS = Path("src/lib/theme.ts")
CSS = Path("src/app/globals.css")
CHARTS = Path("src/data/charts.json")
REPO = Path(__file__).resolve().parents[1]

SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)
STYLE = re.compile(r"<style\b.*?</style>", re.S | re.I)
THEME_MODES_RE = re.compile(r"THEME_MODES\s*=\s*\[(?P<body>[^\]]*)\]")
LITERAL_RE = re.compile(r"'([^']+)'|\"([^\"]+)\"")
LIGHT_FRAME = 'class="chart__frame"'
DARK_MARKER = "chart__frame--dark"


def _modes(theme_src: str) -> list[str]:
    match = THEME_MODES_RE.search(theme_src)
    if not match:
        return []
    return [a or b for a, b in LITERAL_RE.findall(match.group("body"))]


def _media_blocks(css: str) -> list[str]:
    """取出**全部** `@media (prefers-color-scheme: dark)` 的块体（花括号配平）。

    ⚠ 必须取全部：本文件的同款媒体查询**不止一处**（另有令牌/其它组件的分支），
    只取第一个会漏判图表那一段（实测踩到：误报 T2 FAIL）。
    """
    blocks: list[str] = []
    for start in re.finditer(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{", css):
        depth, i = 1, start.end()
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        blocks.append(css[start.end():i - 1])
    return blocks


def check(repo: Path = REPO, out: Path | None = None) -> list[tuple[str, bool, str]]:
    out = out or repo / "out"
    theme_src = (repo / THEME_TS).read_text(encoding="utf-8") if (repo / THEME_TS).exists() else ""
    css = (repo / CSS).read_text(encoding="utf-8") if (repo / CSS).exists() else ""
    results: list[tuple[str, bool, str]] = []

    # T1 强制档同步
    modes = _modes(theme_src)
    forced = [m for m in modes if m != "system"]
    missing = []
    for mode in forced:
        pattern = re.compile(rf"\[data-theme=['\"]{re.escape(mode)}['\"]\][^{{}}]*\.chart__frame")
        if not pattern.search(css):
            missing.append(mode)
    results.append(("T1", bool(forced) and not missing,
                    f"THEME_MODES={modes} · 强制档 {forced} "
                    + ("均有 chart 显隐规则" if not missing else f"缺规则：{missing}")))

    # T2 跟随系统档
    blocks = _media_blocks(css)
    if not blocks:
        results.append(("T2", False, "未找到 @media (prefers-color-scheme: dark) 块"))
    else:
        has_rule = any(".chart__frame" in block for block in blocks)
        scoped = any(
            ".chart__frame" in block
            and (":root:not([data-theme='light'])" in block or ':root:not([data-theme="light"])' in block)
            for block in blocks
        )
        results.append(("T2", has_rule and scoped,
                        f"跟随系统分支（共 {len(blocks)} 个同款媒体块）：chart 规则={has_rule}"
                        f" · 以「非强制浅色」限定={scoped}"))

    # T3 默认态基线
    base = re.search(r"\.chart__frame--dark\s*\{[^}]*display:\s*none", css)
    results.append(("T3", base is not None, "`.chart__frame--dark` 默认 display:none 规则存在"
                    if base else "缺 `.chart__frame--dark { display:none }` 默认态"))

    # T4 数据成对
    charts_path = repo / CHARTS
    if not charts_path.exists():
        results.append(("T4", False, f"{CHARTS} 不存在"))
    else:
        charts = json.loads(charts_path.read_text(encoding="utf-8")).get("charts", [])
        bad = [c.get("key", "?") for c in charts
               if not (c.get("svg", {}).get("light") or "").strip()
               or not (c.get("svg", {}).get("dark") or "").strip()]
        results.append(("T4", bool(charts) and not bad,
                        f"{len(charts)} 张图的 svg.light / svg.dark 均非空"
                        if not bad else f"缺模：{bad}"))

    # T5 产物成对
    pages = sorted(out.rglob("*.html")) if out.exists() else []
    unbalanced = []
    for page in pages:
        raw = page.read_text(encoding="utf-8", errors="replace")
        body = STYLE.sub(" ", SCRIPT.sub(" ", raw))
        light = body.count(LIGHT_FRAME)
        dark = body.count(DARK_MARKER)
        if light or dark:
            if light != dark or light < 1:
                unbalanced.append(f"{page.relative_to(out)}: 浅色 {light} / 深色 {dark}")
    results.append(("T5", not unbalanced,
                    "含图表的页面双模帧成对" if not unbalanced else "不成对：" + "；".join(unbalanced)))
    return results


# ============================ 自检（负向夹具） ============================

CSS_OK = """
.chart__frame { border: 1px solid; }
.chart__frame--dark { display: none; }
[data-theme='dark'] .chart__frame--dark { display: block; }
[data-theme='dark'] .chart__frame:not(.chart__frame--dark) { display: none; }
[data-theme='light'] .chart__frame--dark { display: none; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme='light']) .chart__frame:not(.chart__frame--dark) { display: none; }
  :root:not([data-theme='light']) .chart__frame--dark { display: block; }
}
"""

THEME_OK = "export const THEME_MODES = ['system', 'light', 'dark'] as const;\n"

CHARTS_OK = json.dumps({"charts": [{"key": "demo", "svg": {"light": "<svg/>", "dark": "<svg/>"}}]})

PAGE_OK = (
    'class="chart__frame"</div>'
    'class="chart__frame chart__frame--dark"</div>'
)


def selftest() -> bool:
    ok = True
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        out = repo / "out" / "stats"
        out.mkdir(parents=True)
        (repo / "src" / "lib").mkdir(parents=True)
        (repo / "src" / "app").mkdir(parents=True)
        (repo / "src" / "data").mkdir(parents=True)

        def write_all(css=CSS_OK, theme=THEME_OK, charts=CHARTS_OK, page=PAGE_OK):
            (repo / "src" / "lib" / "theme.ts").write_text(theme, encoding="utf-8")
            (repo / "src" / "app" / "globals.css").write_text(css, encoding="utf-8")
            (repo / "src" / "data" / "charts.json").write_text(charts, encoding="utf-8")
            (out / "index.html").write_text(f"<html><body>{page}</body></html>", encoding="utf-8")

        write_all()
        base = [r for r in check(repo, repo / "out") if not r[1]]
        ok &= not base
        print(f"  [{'PASS' if not base else 'FAIL'}] 对照臂：合成合规样本 FAIL 数 = {len(base)}"
              + (f" · {base}" if base else ""))

        def probe(name: str, criterion: str, **kw):
            nonlocal ok
            write_all(**kw)
            res = check(repo, repo / "out")
            write_all()
            hit = [r for r in res if not r[1] and r[0] == criterion]
            ok &= bool(hit)
            print(f"  [{'PASS' if hit else 'FAIL'}] 夹具 {name} 被抓到 :: " + (hit[0][2] if hit else "未触发"))

        probe("T1 新增主题档未同步 CSS", "T1",
              theme="export const THEME_MODES = ['system', 'light', 'dark', 'sepia'] as const;\n")
        probe("T2 跟随系统分支被删", "T2",
              css=CSS_OK[:CSS_OK.index("@media")])
        probe("T3 默认态基线被删", "T3",
              css=CSS_OK.replace(".chart__frame--dark { display: none; }", ""))
        probe("T4 某张图缺深色模", "T4",
              charts=json.dumps({"charts": [{"key": "demo", "svg": {"light": "<svg/>", "dark": ""}}]}))
        probe("T5 产物缺深色帧", "T5",
              page='class="chart__frame"</div>')

        restored = [r for r in check(repo, repo / "out") if not r[1]]
        ok &= not restored
        print(f"  [{'PASS' if not restored else 'FAIL'}] 恢复后：FAIL 数 = {len(restored)}")
    print(f"\nSELFTEST: {'ALL PASS' if ok else 'HAS FAILURE'}"
          "（每条判据都有能触发它的负向样本）")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(REPO))
    parser.add_argument("--out", default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    repo = Path(args.repo)
    out = Path(args.out) if args.out else repo / "out"
    results = check(repo, out)
    print(f"== 主题三态 × 双模图表同步门控（repo={repo}）==")
    for cid, passed, detail in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {cid}  {detail}")
    ok = all(item[1] for item in results)
    print(f"\nTHEME-STATES: {'ALL PASS' if ok else 'HAS FAILURE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
