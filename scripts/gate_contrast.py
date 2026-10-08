#!/usr/bin/env python3
"""对比度门控 —— 读**真实令牌产物**，不写死字面值。

设计要点（承 0910 主页留档与 0916 令牌用途规范）：
  1. 令牌取自 `src/app/globals.css` 的 `:root`（浅色）与 `:root[data-theme='dark']`
     （深色）两处声明 —— ⛔ 不在本脚本里复制一份色值（复制即第二真相源）。
  2. 阈值只用既有真源：正文 4.5:1（WCAG 2.2 AA 正文），非文本/大字号界面件 3.0:1。
  3. `text.tertiary` 按 0916 `TOKEN-USAGE-SPEC.md` 属**非正文**用途 ⇒ 阈值 3.0，
     但额外报告其相对 4.5 的余量，供「能不能当正文用」的判读。
  4. 空集守卫：任一侧令牌缺失即 FAIL（⛔ 不得静默跳过）。
  5. `--selftest` 内置负向夹具（注入一个低对比度对），验证判据不是恒真。

退出码：0 = ALL PASS；1 = 有失败；2 = 用法/解析错误。
"""

from __future__ import annotations

import argparse
import re
import sys

CSS_PATH = "src/app/globals.css"

# (键, 前景令牌, 背景令牌, 阈值, 用途说明)
CHECKS: list[tuple[str, str, str, float, str]] = [
    ("正文 / 页面底", "text-primary", "surface-page", 4.5, "body"),
    ("正文 / 卡片底", "text-primary", "surface-raised", 4.5, "body"),
    ("正文 / 次级底", "text-primary", "surface-subtle", 4.5, "body"),
    ("二级文字 / 页面底", "text-secondary", "surface-page", 4.5, "body"),
    ("二级文字 / 卡片底", "text-secondary", "surface-raised", 4.5, "body"),
    ("二级文字 / 次级底", "text-secondary", "surface-subtle", 4.5, "body"),
    ("三级灰 / 页面底", "text-tertiary", "surface-page", 3.0, "non-body"),
    ("三级灰 / 次级底", "text-tertiary", "surface-subtle", 3.0, "non-body"),
    ("链接 / 页面底", "link", "surface-page", 4.5, "body"),
    ("链接 / 卡片底", "link", "surface-raised", 4.5, "body"),
    ("品牌底上的前景", "on-brand", "brand-primary", 4.5, "body"),
    ("成功色 / 页面底", "success", "surface-page", 4.5, "non-body"),
    ("警告色 / 页面底", "warning", "surface-page", 4.5, "non-body"),
    ("危险色 / 页面底", "danger", "surface-page", 4.5, "non-body"),
    ("控件描边 / 页面底", "border-line", "surface-page", 3.0, "non-text"),
    ("焦点环 / 页面底", "focus-ring", "surface-page", 3.0, "non-text"),
    ("焦点环 / 卡片底", "focus-ring", "surface-raised", 3.0, "non-text"),
]

REQUIRED = sorted({token for _, fg, bg, _, _ in CHECKS for token in (fg, bg)})


def _srgb(channel: float) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_value: str) -> float:
    raw = hex_value.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    r, g, b = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def extract_block(css: str, selector: str) -> dict[str, str]:
    """取 `selector { ... }` 里所有 `--name: value;` 声明。"""
    pattern = re.compile(re.escape(selector) + r"\s*\{(?P<body>[^}]*)\}", re.S)
    match = pattern.search(css)
    if not match:
        raise SystemExit(f"[用法错误] 在 {CSS_PATH} 中找不到选择器块: {selector}")
    body = match.group("body")
    found: dict[str, str] = {}
    for name, value in re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", body):
        value = value.strip()
        if re.fullmatch(r"#[0-9a-fA-F]{3,8}", value):
            found[name] = value
    return found


def run(palettes: dict[str, dict[str, str]]) -> bool:
    ok = True
    print("== 对比度门控（读 src/app/globals.css 真实令牌）==")
    print(f"   覆盖 {len(REQUIRED)} 个令牌 · {len(CHECKS)} 条检查\n")

    for label, tokens in palettes.items():
        print(f"--- {label} ---")
        for name, fg, bg, threshold, usage in CHECKS:
            if fg not in tokens or bg not in tokens:
                print(f"  [FAIL] {name:18s} 令牌缺失: {fg if fg not in tokens else bg}")
                ok = False
                continue
            value = contrast(tokens[fg], tokens[bg])
            passed = value >= threshold
            ok = ok and passed
            margin = "" if passed else "  <<< 不足"
            note = ""
            if usage == "non-body" and fg.startswith("text-tertiary"):
                note = f"（非正文档；距 4.5 还差 {4.5 - value:+.2f}）" if value < 4.5 else "（亦达正文 4.5）"
            print(
                f"  [{'PASS' if passed else 'FAIL'}] {name:18s} "
                f"{tokens[fg]} on {tokens[bg]} = {value:5.2f}:1 (>= {threshold}){margin}{note}"
            )
        print()

    print("CONTRAST GATE:", "ALL PASS" if ok else "HAS FAILURE")
    return ok


def load_palettes(css_path: str = CSS_PATH) -> dict[str, dict[str, str]]:
    with open(css_path, encoding="utf-8") as handle:
        css = handle.read()
    return {
        "浅色 (:root)": extract_block(css, ":root"),
        "深色 (:root[data-theme='dark'])": extract_block(css, ":root[data-theme='dark']"),
    }


def selftest() -> int:
    """负向夹具：把 on-brand 换成低对比度值，判据必须转 FAIL。"""
    palettes = load_palettes()
    baseline = run(palettes)

    broken = {name: dict(tokens) for name, tokens in palettes.items()}
    for tokens in broken.values():
        tokens["on-brand"] = "#c8c8c8"  # 与浅色品牌底 #1d4ed8 对比度约 2.2:1
    broken_ok = run(broken)

    print("\n== selftest ==")
    print(f"  基线（期望 PASS）: {'PASS' if baseline else 'FAIL'}")
    print(f"  负向夹具（期望 FAIL）: {'PASS' if broken_ok else 'FAIL'}")
    passed = baseline and not broken_ok
    print("  SELFTEST:", "PASS" if passed else "FAIL（判据可能恒真或恒假）")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="对比度门控（读真实令牌产物）")
    parser.add_argument("--selftest", action="store_true", help="跑负向夹具")
    parser.add_argument("--css", default=CSS_PATH, help=f"令牌文件（默认 {CSS_PATH}）")
    args = parser.parse_args()

    try:
        if args.selftest:
            return selftest()
        return 0 if run(load_palettes(args.css)) else 1
    except SystemExit as exc:
        print(exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
