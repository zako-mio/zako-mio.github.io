#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`:hover` 门控机检：产物 CSS 里每一条含 `:hover` 的选择器，是否都位于 `@media (hover:hover)` 之内。

# ─────────────────────────────────────────────────────────────────────────────
# 来源登记（Provenance）：本件是 scripts/probes/ 下的 **CI 活件**（可演进）。
#   · 归档冻结件：Mission-file/2026-10/1008-个人主页深化改革/batch8-evidence/check_hover_gating.py
#                  @ 1a06be5 · sha256=24a887cf5672867e955868cdef3c4f12e16592a492c9f63061347f4fca74089c
#   · 漂移方向：本件可演进；归档件⛔ 不追改、不自动同步（保其批报告的逐字节可复现）。
#   · 登记表：scripts/probes/PROVENANCE.json（机检 scripts/probes/check_provenance.py）
#   · 相对归档件的改动（第八批 §4-② 硬化）：① 从「一次性脚本」改为 argparse 函数化；
#     ② 路径改为**cwd 无关**（默认以仓库根定位，可用 --root 覆盖）；
#     ③ 产物 CSS 缺失时以 rc=2 退出（`[用法错误]`，⛔ 不读成判据 FAIL）；
#     ④ 产物 CSS 多文件时**全量拼接**（归档件只取 `[0]`；本项目当前仅 1 个文件，二者等价）；
#     ⑤ 新增 --selftest（合成 CSS 夹具，验判据非恒真）。
#     ⛔ 解析规则（进入规则体期间不累积选择器；@media 入栈；伪元素归一化）一字未改。
# ─────────────────────────────────────────────────────────────────────────────

解析规则：进入规则体（`{` 后到配对 `}`）期间不累积选择器文本；`@media` 作为上下文入栈。
注意：minified CSS 会把 `::after` 写成 `:after` ⇒ 源/产物集合比对必须做伪元素归一化，否则**假 FAIL**。

用法：
    python3 scripts/probes/hover_gating_probe.py                 # 读 out/ 产物 ＋ src/app/globals.css
    python3 scripts/probes/hover_gating_probe.py --selftest      # 合成 CSS 夹具（不读仓库产物）
    python3 scripts/probes/hover_gating_probe.py --root <dir>
    set -e; pnpm build    # ⛔ 读 out/ ⇒ 必须先构建，否则 rc=2 退出（[用法错误]，非判据 FAIL）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_GLOB = "out/_next/static/css/*.css"
SOURCE_CSS = "src/app/globals.css"


def parse_hover(css: str) -> tuple[list[str], list[str]]:
    """返回 (受 @media(hover:hover) 门控的 :hover 选择器, 未门控的)。"""
    stack: list[tuple[str, bool | None]] = []  # ('media', isHover) | ('rule', None)
    head = ""
    gated: list[str] = []
    ungated: list[str] = []
    i, n = 0, len(css)
    while i < n:
        c = css[i]
        if c == "{":
            h = head.strip()
            head = ""
            if h.startswith("@media"):
                stack.append(("media", "hover:hover" in h.replace(" ", "")))
            elif h.startswith("@"):
                stack.append(("media", False))
            else:
                stack.append(("rule", None))
                hov = [s.strip() for s in h.split(",") if ":hover" in s]
                if hov:
                    (gated if any(k == "media" and v for k, v in stack[:-1]) else ungated).extend(hov)
        elif c == "}":
            if stack:
                stack.pop()
        elif not (stack and stack[-1][0] == "rule"):
            head += c
        i += 1
    return gated, ungated


def norm(xs) -> set[str]:
    return {re.sub(r"\s+", "", x).replace("::", ":") for x in xs}


def source_hover(css: str) -> set[str]:
    """源码侧 :hover 选择器集合（去注释、排除 at-rule 选择器块）。"""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    sel_re = re.compile(r"([^{}]+)\{([^{}]*)\}")
    out: set[str] = set()
    for m in sel_re.finditer(css):
        if "@" in m.group(1):
            continue
        for s in m.group(1).split(","):
            if ":hover" in s:
                out.add(s.strip())
    return out


# ---------------------------------------------------------------- selftest
# ★ 判据必须能 FAIL，否则是哑火门控（恒真）。夹具直接喂给**同一个解析器**，逐例断言。
SELFTEST_FIXTURES = [
    (".a:hover{color:red}", 0, 1, "顶层 :hover 视为未门控（负向夹具必须被抓到）"),
    ("@media (hover:hover){.b:hover{color:red}}", 1, 0, "位于 hover:hover 内视为已门控"),
    ("@media(hover:hover){.c:hover{color:red}}", 1, 0, "minified 无空格同样识别"),
    ("@media (min-width:1px){@media (hover:hover){.d:hover{color:red}}}", 1, 0, "嵌套 media 内仍判已门控"),
    ("@media (hover:none){.e:hover{color:red}}", 0, 1, "hover:none 不构成门控（负例）"),
    ("@media (hover:hover) and (min-width:1px){.f:hover,.g:hover{color:red}}", 2, 0, "多选择器逐个判定"),
]


def selftest() -> int:
    checks: list[tuple[str, bool]] = []
    for css, want_gated, want_ungated, desc in SELFTEST_FIXTURES:
        g, u = parse_hover(css)
        ok = len(g) == want_gated and len(u) == want_ungated
        checks.append((f"{desc}｜期望 gated={want_gated}/ungated={want_ungated}，实得 {len(g)}/{len(u)}", ok))
    # 伪元素归一化（防 minified `::after`→`:after` 造成的假 FAIL）
    norm_ok = norm(["a::after:hover"]) == norm(["a:after:hover"])
    checks.append(("伪元素归一化 ::after → :after 生效（防假 FAIL）", norm_ok))

    print("== selftest（合成 CSS；⛔ 不读仓库产物）==")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    good = all(ok for _, ok in checks)
    print("  SELFTEST:", "PASS" if good else "FAIL（判据可能恒真）")
    return 0 if good else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="产物 CSS 的 :hover 是否全在 @media (hover:hover) 内")
    ap.add_argument("--root", type=Path, default=REPO_ROOT, help=f"仓库根（缺省 {REPO_ROOT}）")
    ap.add_argument("--selftest", action="store_true", help="合成 CSS 夹具，验证判据非恒真")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    root = args.root.resolve()
    css_files = sorted(root.glob(ARTIFACT_GLOB))
    if not css_files:
        print(f"[用法错误] 未找到 {root/ARTIFACT_GLOB}（先 `pnpm build`；⛔ 这不是判据 FAIL）")
        return 2
    source = root / SOURCE_CSS
    if not source.exists():
        print(f"[用法错误] 未找到 {source}")
        return 2

    css = "\n".join(p.read_text(encoding="utf-8") for p in css_files)
    gated, ungated = parse_hover(css)

    print(f"产物：{', '.join(str(p.relative_to(root)) for p in css_files)}")
    print(f"[GATED] 受 @media (hover:hover) 门控的 :hover 选择器：{len(gated)} 条")
    print(f"[UNGATED] ⛔ 未门控：{len(ungated)} 条")
    for s in ungated:
        print("   [UNGATED]", s)

    src_hover = source_hover(source.read_text(encoding="utf-8"))
    same = norm(src_hover) == norm(gated)
    print(f"\n源 :hover {len(norm(src_hover))} 条 · 产物门控 {len(norm(gated))} 条 → 集合{'一致' if same else '不一致'}")
    if not same:
        print("  源多出：", sorted(norm(src_hover) - norm(gated)))
        print("  产物多出：", sorted(norm(gated) - norm(src_hover)))

    ok = not ungated and same
    print(f"\nHOVER GATING: {'ALL PASS' if ok else 'HAS FAILURE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
