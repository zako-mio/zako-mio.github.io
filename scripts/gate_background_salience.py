#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""背景显著性门控（治理层·批七）—— 背景层**结构护栏** ＋ 显著性**报告项**。

为什么需要它：批六把对比度问题解决了（令牌对与合成实测全过），但用户报的「背景抢焦点」
是**显著性/层级**问题 —— 阈值型门控（对比度 ≥4.5）结构性看不见它。
本门控做两件事，且**严格区分两者的强度**：

  【护栏：fail-closed，可判】
    B1 背景容器必须不可交互：`.backdrop` 声明 `pointer-events: none`，且其 `z-index` 为负
       （或显式 `isolation: isolate` 形成独立层叠上下文）。
    B2 背景子树不得含可聚焦内容：全量产物的 `.backdrop` 子树里出现 a/button/input/select/
       textarea/[tabindex] 即 FAIL（背景一旦可聚焦，就会把键盘用户拽进装饰件）。
    B3 动效熔断必须是**全局**且不可绕过：
       (a) `@media (prefers-reduced-motion: reduce)` 内存在 `*` 级 animation 压制；
       (b) `:root[data-motion='off']` 内存在 `*` 级 animation 压制；
       且背景类规则里不得用 `animation-duration: … !important` 绕过熔断。

  【报告项：⛔ 不判阈值】
    背景层数 / 运动层数 / 纱幕档位 / 网格遮罩峰值 / 照片 opacity 与 filter。
    ⇒ 依本项目既定口径（criterion-design-validation）：**代理指标不得接自动回写**；
      「背景是否抢焦点」的显著性（局部对比/高频能量）尚未验证与目标同向，
      故只输出读数供人审阅，**不据此判 PASS/FAIL**。

用法：
    python3 scripts/gate_background_salience.py
    python3 scripts/gate_background_salience.py --selftest
退出码：0 = ALL PASS；1 = 有 FAIL；2 = 用法/解析错误。
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
OUT_DIR = ROOT / "out"

FOCUSABLE = re.compile(r"<(a|button|input|select|textarea)\b|[^>]*\btabindex\s*=", re.I)
TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)\b([^>]*)>")


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def block_of(css: str, selector: str) -> str | None:
    m = re.search(re.escape(selector) + r"\s*\{(?P<body>[^}]*)\}", css, re.S)
    return m.group("body") if m else None


def backdrop_subtree(html: str) -> str | None:
    """用标签栈截出 `.backdrop` 的第一个元素子树（⛔ 不靠缩进/正则贪婪）。"""
    start = re.search(r"<(div|[a-z]+)\b[^>]*class=\"backdrop\"[^>]*>", html)
    if not start:
        return None
    depth = 0
    for m in TAG.finditer(html, start.start()):
        closing = m.group(1) == "/"
        attrs = m.group(3) or ""
        self_closing = attrs.rstrip().endswith("/") or m.group(2).lower() in {
            "br", "img", "input", "hr", "meta", "link", "source", "path", "circle", "rect",
        }
        if not closing:
            depth += 1
            if self_closing:
                depth -= 1
        else:
            depth -= 1
        if depth <= 0 and closing:
            return html[start.start(): m.end()]
    return None


def has_global_animation_breaker(css: str, scope_pattern: str) -> bool:
    """在指定作用域里找 `*` 级 animation 压制。

    ⚠ 必须同时处理**两种书写形态**（本判据第一版只处理了形态 A，导致基线假 FAIL）：
      形态 A｜at-rule 包裹：`@media (...) { * { animation-… } }` ⇒ 块体里含嵌套规则；
      形态 B｜普通选择器：  `:root[data-motion='off'] * { animation-… }` ⇒ 它自身就是规则，
              块体是声明，`*` 出现在**选择器**里。
    """
    for m in re.finditer(r"(" + scope_pattern + r"[^{]*)\{", css):
        head = m.group(1)
        depth, i = 0, m.end() - 1
        while i < len(css):
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = css[m.end(): i]

        nested = list(re.finditer(r"([^{}]+)\{([^{}]*)\}", body))
        if nested:                                  # 形态 A
            for rule in nested:
                sel, decl = rule.group(1), rule.group(2)
                if "*" in sel and "animation" in decl:
                    return True
        elif "*" in head and "animation" in body:   # 形态 B
            return True
    return False


def run(css_path: Path, out_dir: Path) -> tuple[bool, list[str]]:
    ok = True
    findings: list[str] = []
    css = strip_comments(css_path.read_text(encoding="utf-8"))

    print("== 背景显著性门控（背景层结构护栏 + 显著性报告项）==")

    # ---- B1 背景容器不可交互
    print("\n--- B1 背景容器必须不可交互 ---")
    backdrop = block_of(css, ".backdrop")
    if backdrop is None:
        print("  [FAIL] 找不到 `.backdrop` 规则块（结构变更？）")
        ok = False
    else:
        pe = "pointer-events" in backdrop and "none" in backdrop
        print(f"  [{'PASS' if pe else 'FAIL'}] `.backdrop` pointer-events: none = {pe}")
        ok = ok and pe
        if not pe:
            findings.append("B1 .backdrop 未禁用命中测试")
        z = re.search(r"z-index\s*:\s*(-?\d+)", backdrop)
        zok = bool(z) and int(z.group(1)) < 0
        print(f"  [{'PASS' if zok else 'FAIL'}] `.backdrop` z-index 为负 = {z.group(1) if z else '缺'}")
        ok = ok and zok
        if not zok:
            findings.append("B1 .backdrop 未置于内容之下")

    # ---- B2 背景子树不得含可聚焦内容
    print("\n--- B2 背景子树不得含可聚焦内容（全量产物）---")
    pages = sorted(out_dir.rglob("*.html")) if out_dir.exists() else []
    if not pages:
        print("  [FAIL] out/ 不存在或无页面 —— 本门控读真实产物，请先 pnpm build")
        ok = False
    else:
        leaked: list[str] = []
        scanned = 0
        for page in pages:
            html = page.read_text(encoding="utf-8", errors="replace")
            sub = backdrop_subtree(html)
            if sub is None:
                continue
            scanned += 1
            if FOCUSABLE.search(sub):
                leaked.append(str(page.relative_to(out_dir.parent)))
        print(f"  [{'PASS' if not leaked else 'FAIL'}] 扫描 {scanned}/{len(pages)} 页 · "
              f"背景子树内可聚焦元素：{leaked or '无'}")
        ok = ok and not leaked
        if leaked:
            findings.append(f"B2 背景子树含可聚焦内容：{leaked}")

    # ---- B3 动效熔断必须全局且不可绕过
    print("\n--- B3 动效熔断（全局且不可绕过）---")
    rm = has_global_animation_breaker(css, r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)")
    print(f"  [{'PASS' if rm else 'FAIL'}] prefers-reduced-motion 下有 `*` 级 animation 压制 = {rm}")
    ok = ok and rm
    if not rm:
        findings.append("B3 reduced-motion 全局熔断缺失")
    off = has_global_animation_breaker(css, r":root\[data-motion='off'\]")
    print(f"  [{'PASS' if off else 'FAIL'}] [data-motion='off'] 下有 `*` 级 animation 压制 = {off}")
    ok = ok and off
    if not off:
        findings.append("B3 动效开关全局熔断缺失")

    bypass = [sel for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
              if "backdrop" in sel and re.search(r"animation-duration\s*:[^;]*!important", decl)]
    print(f"  [{'PASS' if not bypass else 'FAIL'}] 背景类未用 !important 绕过熔断（越权：{bypass or '无'}）")
    ok = ok and not bypass
    if bypass:
        findings.append(f"B3 背景类绕过熔断：{bypass}")

    # ---- 报告项（⛔ 不判阈值）
    print("\n--- 报告项（⛔ 不判 PASS/FAIL；显著性代理量必须先验证同向性）---")
    layers = sorted({c for c in re.findall(r"\.backdrop__[\w-]+", css)})
    animated = []
    for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if "backdrop" in sel and re.search(r"^\s*animation\s*:", decl, re.M):
            animated.append(" ".join(sel.split()))
    print(f"  · 背景类总数（含修饰类）：{len(layers)}")
    print(f"  · 声明 animation 的背景选择器：{len(animated)} 条 → {animated}")
    veil = [(name, decl) for name, decl in re.findall(r"\.backdrop__veil--(\w+)\s*\{([^}]*)\}", css, re.S)
            if "gradient" in decl]        # ⚠ 只取真正的纱幕规则：分帧规则（display:none）也含同名类
    for name, decl in veil:
        stops = re.findall(r"color-mix\(in srgb, var\(--surface-page\)\s*(\d+)%", decl)
        print(f"  · 纱幕 [{name}] 档位：{stops or '（未解析到档位）'}")
    grid = block_of(css, ".backdrop__grid")
    if grid:
        m = re.search(r"radial-gradient\(([^)]*)\)", grid)
        print(f"  · 网格遮罩：{m.group(1).strip() if m else '（未解析到）'} ← ⚠ 峰值位置决定它在正文处有多强")
    # ★ 批八：局部 scrim ＋ 阅读带边界（裁决③ 分区）。报告项：⛔ 不判阈值。
    scrim = block_of(css, ".backdrop__scrim")
    if scrim:
        stops = re.findall(r"var\(--scrim-(\d)\)", scrim)
        band = dict(re.findall(r"--backdrop-reading-(top|left)\s*:\s*([^;]+);", css))
        print(f"  · 局部 scrim（分区）档位令牌：{stops or '（未解析到）'}"
              f" · 阅读带边界 top={band.get('top', '?')} left={band.get('left', '?')}"
              "  ← ⚠ 只压阅读带；非阅读带保持照片原样")
    photo = block_of(css, ".backdrop__photo--night")
    if photo:
        op = re.search(r"opacity\s*:\s*([\d.]+)", photo)
        fl = re.search(r"filter\s*:\s*([^;]+)", photo)
        print(f"  · 夜间照片：opacity={op.group(1) if op else '-'} · filter={fl.group(1).strip() if fl else '-'}"
              "  ← ⚠ contrast 提高内部反差 = 提高背景显著性（与「不抢焦点」反向）")

    print("\nBACKGROUND SALIENCE GATE:", "ALL PASS" if ok else "HAS FAILURE")
    return ok, findings


# ───────────────────────────── 负向夹具 ─────────────────────────────

CSS_OK = """
.backdrop { position: fixed; inset: 0; z-index: -1; pointer-events: none; }
.backdrop__photo { animation: drift 160s infinite alternate; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.001ms !important; }
}
:root[data-motion='off'] *, :root[data-motion='off'] *::after {
  animation-duration: 0.001ms !important;
}
"""
HTML_OK = '<div class="backdrop" aria-hidden="true"><span class="backdrop__photo"></span></div>'


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

        ok, _ = run(*fixture("base", CSS_OK, HTML_OK))
        cases.append(("基线：护栏齐备、背景子树无交互件", ok))

        ok, _ = run(*fixture("b1", CSS_OK.replace("pointer-events: none;", "pointer-events: auto;"), HTML_OK))
        cases.append(("负向夹具1：.backdrop 未禁用命中测试（期望 FAIL）", not ok))

        ok, _ = run(*fixture("b1b", CSS_OK.replace("z-index: -1;", "z-index: 1;"), HTML_OK))
        cases.append(("负向夹具2：.backdrop 未置于内容之下（期望 FAIL）", not ok))

        leaky = ('<div class="backdrop" aria-hidden="true">'
                 '<span class="backdrop__photo"></span><a href="/x">漏进背景的链接</a></div>')
        ok, _ = run(*fixture("b2", CSS_OK, leaky))
        cases.append(("负向夹具3：背景子树含可聚焦链接（期望 FAIL）", not ok))

        no_rm = CSS_OK.split("@media")[0]
        ok, _ = run(*fixture("b3", no_rm, HTML_OK))
        cases.append(("负向夹具4：缺失全局动效熔断（期望 FAIL）", not ok))

        byp = CSS_OK + "\n.backdrop__photo { animation-duration: 5s !important; }\n"
        ok, _ = run(*fixture("b3b", byp, HTML_OK))
        cases.append(("负向夹具5：背景类用 !important 绕过熔断（期望 FAIL）", not ok))

    print("\n== selftest ==")
    for name, passed in cases:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    all_ok = all(p for _, p in cases)
    print("  SELFTEST:", "PASS" if all_ok else "FAIL（判据可能恒真或恒假）")
    return 0 if all_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="背景显著性门控（结构护栏 + 报告项）")
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
