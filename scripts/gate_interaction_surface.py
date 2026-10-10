#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互作用面门控（治理层·批七）——「悬停反馈面 ≡ 点击热区」的**关系型**判据。

为什么需要它：本站此前的门控都是**阈值型**（对比度 ≥4.5、溢出 =0、首屏 JS ≤106 kB…），
而「悬停有反馈、点击无响应」这类缺陷是**关系型**的 —— 阈值门控结构性看不见它。
本门控把这条关系提升为可机检的契约。

判据（C1–C4，全部静态可跑，CI 无需浏览器）：
  C1 双向闭合：`globals.css` 里含 `:hover` / `:focus-within` 的选择器集合
               ⟺ `scripts/interaction-surfaces.json` 的登记集合
               （漏登记 ⇒ FAIL；登记了却无对应规则 ⇒ FAIL。呼应既有 A7/A8 的清单一致性口径）
  C2 空集守卫：每条登记的「去伪类基选择器」必须在该**全量产物**（out 下所有页面）里至少命中 1 个元素
               ⇒ 防登记表随改名/删除而**静默腐化**（⛔ 不得静默跳过）
  C3 覆盖率契约：kind ∈ {self, container} 必须声明 coverage_min ≥ 0.98；
                若 status == "rework"（已知缺陷）则允许低于契约，但**必须**带 deadzone_note + expires_at，
                且本条判 WARN（⛔ 到期未处理应升级为 FAIL；降级须预登记）
  C4 焦点等价：kind ∈ {self, container} 必须有焦点等价面（`focus_equivalent` 指向真实存在的焦点规则，
                或显式 `:focus-visible` 全局环）；container 缺失且未登记 rework ⇒ FAIL

  ★ 批十三新增 kind=decor（装饰性反射面）：
    放宽（**用户裁决** 2026-10-10：V1「所有带边框/圆角容器统一加指针特效」与本站
    「悬停反馈面 ≡ 点击热区」判据互锁 ⇒ 裁决走「新增 kind ＋ 更严替代判据」）：
      · C3 覆盖率契约**不适用**（装饰层不暗示可点击，无「反馈面 > 热区」的假可供性问题）；
      · C4 焦点等价**不适用**（装饰层无「键盘用户看不到鼠标看到的反馈」这一信息等价问题）。
    ⛔ 但**不**放宽：C1 双向闭合 / C2 空集守卫 照旧适用（装饰面同样不得漏登记、不得腐化）。
    替代判据在浏览器层（`surface_hit_probe.py` 的 decor 分支）：D1 cursor 语义不得变为 pointer；
    D2 面内**含交互目标** ⇒ 回退按 container 口径判覆盖率（⛔ 防「用 decor 盖章逃过覆盖率」）。


判据自身的不覆盖面（⛔ 不得把「零命中」读成「无消费方」）：
  · 真实覆盖率（面积比）须浏览器实测 ⇒ 本门控只校验**契约是否被声明且未腐化**；
  · 本门控**不判**「每个可点目标是否都有 hover 反馈」（欠反馈方向，需 DOM 求值）。
  ⇒ 上述两面由 `batch7-evidence/audit_site.py`（浏览器层，提示词级）承担，清单见本文件的 OUTPUT 段。

用法：
    python3 scripts/gate_interaction_surface.py
    python3 scripts/gate_interaction_surface.py --selftest
退出码：0 = ALL PASS（可含 WARN）；1 = 有 FAIL；2 = 用法/解析错误。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "src/app/globals.css"
TABLE_PATH = ROOT / "scripts/interaction-surfaces.json"
OUT_DIR = ROOT / "out"

VALID_KINDS = {"self", "descendant", "container", "decor"}
VALID_STATUS = {"ok", "rework"}

# C3/C4 只适用于「反馈面」类；decor 是装饰性反射面（批十三），两条均不适用。
FEEDBACK_KINDS = {"self", "container"}


# ───────────────────────────── 解析 ─────────────────────────────

def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def all_selectors(css: str) -> list[str]:
    """抽出所有选择器（拆逗号组），跳过 at-rule 与前导的 at-rule 文本。"""
    out: list[str] = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", strip_comments(css)):
        head = match.group(1)
        if "@" in head:
            continue
        for part in head.split(","):
            sel = " ".join(part.split())
            if sel:
                out.append(sel)
    return out


def hover_selectors(css: str) -> set[str]:
    return {s for s in all_selectors(css) if ":hover" in s or ":focus-within" in s}


def focus_selectors(css: str) -> set[str]:
    return {s for s in all_selectors(css) if ":focus" in s}


def base_selector(sel: str) -> str:
    """去掉伪类/伪元素（保留后代结构）→ 用于在产物里做命中检查。"""
    stripped = re.sub(r"::?[a-zA-Z-]+(\([^)]*\))?", " ", sel)
    return " ".join(stripped.split())


def last_compound(sel: str) -> str:
    """取选择器**最后一个复合选择器**（去掉组合子），用于空集守卫。

    ⚠ 不判嵌套关系（本门控不做 DOM 求值）；只要求该复合选择器在产物里存在，
      足以抓住「选择器被改名/删除」造成的登记表腐化。
    """
    cleaned = re.sub(r"\b(>|\+|~)\b", " ", base_selector(sel))
    parts = cleaned.split()
    return parts[-1] if parts else ""


# ───────────────────────── 产物元素索引 ─────────────────────────

TAG_RE = re.compile(r"<([a-zA-Z][\w-]*)\b([^>]*)>")
ATTR_RE = re.compile(r"([a-zA-Z_:][\w:.-]*)(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?")


def attr_names(attrs: str) -> set[str]:
    """取该标签**出现过的属性名**集合（含无值属性）。

    ★ 批十三：C2 的空集守卫原本只看 tag/class，于是 `[data-spotlight]`（属性选择器）
      永远零命中 ⇒ 会产出**假 FAIL**。本函数把「属性存在性」纳入可判面，
      与 compound_hits 的 `[attr]` 分支配套。
    """
    return {m.group(1).lower() for m in ATTR_RE.finditer(attrs)}


def out_elements(out_dir: Path) -> list[tuple[str, set[str], set[str]]]:
    """扫**全量**产物页面（⛔ 不用委派清单，覆盖同类项全集），返回 [(tag, {class}, {attr})]。"""
    elements: list[tuple[str, set[str], set[str]]] = []
    if not out_dir.exists():
        return elements
    for page in sorted(out_dir.rglob("*.html")):
        html = page.read_text(encoding="utf-8", errors="replace")
        for match in TAG_RE.finditer(html):
            tag = match.group(1).lower()
            attrs = match.group(2)
            cls = re.search(r'class="([^"]*)"', attrs)
            classes = set(cls.group(1).split()) if cls else set()
            elements.append((tag, classes, attr_names(attrs)))
    return elements


def compound_hits(elements: list[tuple[str, set[str], set[str]]], compound: str) -> int:
    """统计复合选择器在元素集合里的命中数。

    支持形式：`tag` / `.a` / `tag.a` / `.a.b` / `[attr]` / `tag[attr]`。
    ⛔ 不支持伪类/伪元素/后代组合（本门控不做 DOM 求值）。
    """
    if not compound:
        return 0
    tag_part = ""
    classes: list[str] = []
    attrs: list[str] = []
    for token in re.findall(r"^[a-zA-Z][\w-]*|\.[\w-]+|\[[\w:.-]+\]", compound):
        if token.startswith("."):
            classes.append(token[1:])
        elif token.startswith("["):
            attrs.append(token[1:-1].lower())
        else:
            tag_part = token.lower()
    if not tag_part and not classes and not attrs:
        return 0
    hits = 0
    for tag, cls, attr in elements:
        if tag_part and tag != tag_part:
            continue
        if not all(c in cls for c in classes):
            continue
        if not all(a in attr for a in attrs):
            continue
        hits += 1
    return hits


# ───────────────────────────── 判据 ─────────────────────────────

def run(css_path: Path, table_path: Path, out_dir: Path) -> tuple[bool, list[str]]:
    findings: list[str] = []
    ok = True

    css = css_path.read_text(encoding="utf-8")
    table = json.loads(table_path.read_text(encoding="utf-8"))
    entries = table.get("entries", [])
    css_hover = hover_selectors(css)
    css_focus = focus_selectors(css)
    declared = {e["selector"] for e in entries}

    print("== 交互作用面门控（反馈面 ≡ 热区）==")
    print(f"   CSS :hover/:focus-within 选择器 {len(css_hover)} 条 · 登记 {len(entries)} 条 · "
          f"产物页面 {len(list(out_dir.rglob('*.html'))) if out_dir.exists() else 0} 个\n")

    # ---- C1 双向闭合
    print("--- C1 双向闭合（漏登记 / 幽灵登记）---")
    missing = sorted(css_hover - declared)
    ghost = sorted(declared - css_hover)
    for sel in missing:
        print(f"  [FAIL] 未登记：`{sel}`（CSS 里有规则，声明表缺失）")
    for sel in ghost:
        print(f"  [FAIL] 幽灵登记：`{sel}`（声明表有，CSS 里无对应规则）")
    if not missing and not ghost:
        print(f"  [PASS] {len(css_hover)} 条选择器与声明表完全闭合")
    else:
        ok = False
        findings.append(f"C1 双向闭合失败：漏登记 {len(missing)} · 幽灵 {len(ghost)}")

    # ---- 逐条
    elements = out_elements(out_dir)
    print("\n--- C2 空集守卫（基选择器须在全量产物里命中）---")
    rework: list[str] = []
    warns: list[str] = []
    for entry in entries:
        sel = entry["selector"]
        kind = entry.get("kind")
        status = entry.get("status", "ok")

        if kind not in VALID_KINDS:
            print(f"  [FAIL] `{sel}` kind 非法：{kind!r}")
            ok = False
            continue
        if status not in VALID_STATUS:
            print(f"  [FAIL] `{sel}` status 非法：{status!r}")
            ok = False
            continue

        probe = last_compound(entry.get("hotspot") or sel)
        hits = compound_hits(elements, probe)
        if hits == 0:
            print(f"  [FAIL] `{sel}` 热区探针 `{probe}` 在全量产物里零命中（登记表已腐化？）")
            ok = False
            findings.append(f"C2 `{probe}` 零命中")
        else:
            print(f"  [PASS] `{sel}` 热区探针 `{probe}` 命中 {hits} 处")

        # ---- C3 覆盖率契约
        # ⚠ 以 `status` 为**唯一裁决字段**（第一版以 coverage_min 触发，导致
        #   coverage_min=0.98 的 rework 条目被整段跳过、静默漏登记 ⇒ 已修）。
        if kind == "decor":
            # ★ 批十三：装饰性反射面 ⇒ C3/C4 不适用（放宽依据＝用户裁决，见模块 docstring）。
            #   ⛔ 打印出来，避免「豁免」变成静默行为；替代判据 D1/D2 在浏览器层。
            print(f"  [PASS] `{sel}` decor ⇒ C3 覆盖率 / C4 焦点等价**不适用**；"
                  f"替代判据＝探针 D1(cursor) + D2(含交互目标者回退按 container 口径)")
        elif kind in FEEDBACK_KINDS:
            cov = entry.get("coverage_min")
            if status == "rework":
                has_meta = bool(entry.get("deadzone_note")) and bool(entry.get("expires_at"))
                if not has_meta:
                    print(f"  [FAIL] `{sel}` 登记为 rework 但缺 deadzone_note/expires_at")
                    ok = False
                    findings.append(f"C3 `{sel}` rework 元数据缺失")
                elif not isinstance(cov, (int, float)):
                    print(f"  [FAIL] `{sel}` rework 条目仍须声明目标契约 coverage_min")
                    ok = False
                    findings.append(f"C3 `{sel}` 缺目标契约")
                else:
                    rework.append(sel)
            elif not isinstance(cov, (int, float)) or cov < 0.98:
                print(f"  [FAIL] `{sel}` coverage_min 缺失或 < 0.98（status=ok 即要求反馈面≡热区）")
                ok = False
                findings.append(f"C3 `{sel}` coverage_min 不合契约")

        # ---- C4 焦点等价
        if kind in FEEDBACK_KINDS:
            fe = entry.get("focus_equivalent")
            if fe == ":focus-visible":
                if ":focus-visible" not in css_focus:
                    print(f"  [FAIL] `{sel}` 声明依赖全局 :focus-visible，但 CSS 里没有该规则")
                    ok = False
                    findings.append(f"C4 `{sel}` 全局焦点环缺失")
            elif fe:
                if fe not in css_focus:
                    if status == "rework":
                        warns.append(f"`{sel}` 焦点等价面 `{fe}` 尚未落地（rework）")
                    else:
                        print(f"  [FAIL] `{sel}` 焦点等价面 `{fe}` 在 CSS 里不存在")
                        ok = False
                        findings.append(f"C4 `{sel}` 焦点等价面不存在")
            else:
                if status == "rework":
                    warns.append(f"`{sel}` 缺焦点等价面（rework：键盘用户看不到鼠标看到的反馈）")
                else:
                    print(f"  [FAIL] `{sel}` 缺 focus_equivalent（有 hover 就必须有焦点等价，WCAG 1.4.13）")
                    ok = False
                    findings.append(f"C4 `{sel}` 缺焦点等价")

    # ---- 汇总
    print("\n--- 汇总 ---")
    by_kind: dict[str, int] = {}
    for entry in entries:
        by_kind[entry.get("kind", "?")] = by_kind.get(entry.get("kind", "?"), 0) + 1
    print(f"  对象分类：{by_kind}")
    print(f"  已知缺陷（rework，只 WARN）：{len(rework)} 条")
    for sel in rework:
        print(f"    ⚠ {sel}")
    for w in warns:
        print(f"    ⚠ {w}")
    if not rework and not warns:
        print("    无")

    print("\n--- 不覆盖面（⛔ 不得把「零命中」读成「无消费方」）---")
    for line in table.get("not_covered", []):
        print(f"  · {line}")

    print("\nINTERACTION SURFACE GATE:",
          "ALL PASS" + (f"（含 {len(rework) + len(warns)} 条 WARN）" if (rework or warns) else "")
          if ok else "HAS FAILURE")
    return ok, findings


# ───────────────────────────── 负向夹具 ─────────────────────────────

FIXTURE_CSS_OK = """
:root { --x: #fff; }
.button:hover { color: red; }
:focus-visible { outline: 2px solid blue; }
"""


def _mk_fixture(tmp: Path, css: str, entries: list[dict], html: str):
    css_p = tmp / "globals.css"
    table_p = tmp / "table.json"
    out_p = tmp / "out"
    out_p.mkdir(parents=True, exist_ok=True)
    css_p.write_text(css, encoding="utf-8")
    table_p.write_text(json.dumps({"entries": entries, "not_covered": []}, ensure_ascii=False), encoding="utf-8")
    (out_p / "index.html").write_text(html, encoding="utf-8")
    return css_p, table_p, out_p


def selftest() -> int:
    ok_entry = {
        "selector": ".button:hover", "kind": "self", "hotspot": "a.button",
        "coverage_min": 0.98, "focus_equivalent": ":focus-visible", "status": "ok",
        "reason": "夹具",
    }
    html = '<a class="button" href="/x">go</a>'
    rework_entry = {
        "selector": ".card:hover", "kind": "container", "hotspot": ".card__title a",
        "coverage_min": 0.5, "focus_equivalent": None, "status": "rework",
        "deadzone_note": "夹具", "expires_at": "夹具", "reason": "夹具",
    }
    css_rework = FIXTURE_CSS_OK + "\n.card:hover { color: red; }\n"
    html_rework = html + '<article class="card"><h3 class="card__title"><a href="/y">t</a></h3></article>'

    cases: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # 基线（期望 PASS）
        a = _mk_fixture(tmp / "base", FIXTURE_CSS_OK, [ok_entry], html)
        ok, _ = run(*a)
        cases.append(("基线：表与 CSS 闭合、热区命中、契约齐备", ok))

        # 负向样本 1：CSS 新增未登记的 hover 规则
        b = _mk_fixture(tmp / "c1", FIXTURE_CSS_OK + "\n.ghost:hover { color: red; }\n", [ok_entry], html)
        ok, _ = run(*b)
        cases.append(("负向夹具1：新增未登记的 :hover 规则（期望 FAIL）", not ok))

        # 负向夹具 2：幽灵登记
        c = _mk_fixture(tmp / "c2", FIXTURE_CSS_OK,
                        [ok_entry, {**ok_entry, "selector": ".nowhere:hover"}], html)
        ok, _ = run(*c)
        cases.append(("负向夹具2：登记表里的幽灵选择器（期望 FAIL）", not ok))

        # 负向夹具 3：热区零命中（登记表腐化）
        d = _mk_fixture(tmp / "c3", FIXTURE_CSS_OK,
                        [{**ok_entry, "hotspot": "a.renamed-away"}], '<span>no link</span>')
        ok, _ = run(*d)
        cases.append(("负向夹具3：热区探针在产物里零命中（期望 FAIL）", not ok))

        # 对照臂：已知缺陷登记为 rework ⇒ 应 PASS（含 WARN），⛔ 不得因已知缺陷红灯挡路
        e = _mk_fixture(tmp / "rework", css_rework, [ok_entry, rework_entry], html_rework)
        ok, _ = run(*e)
        cases.append(("对照臂：已知缺陷按 rework 预登记 ⇒ 应 PASS（含 WARN）", ok))

        # 负向夹具 4：status=ok 却 coverage 不合契约
        bad = {**ok_entry, "coverage_min": 0.10}
        f = _mk_fixture(tmp / "c3b", FIXTURE_CSS_OK, [bad], html)
        ok, _ = run(*f)
        cases.append(("负向夹具4：status=ok 但 coverage_min=0.10（期望 FAIL）", not ok))

        # 负向夹具 5：缺焦点等价面且未登记 rework
        g = _mk_fixture(tmp / "c4", FIXTURE_CSS_OK,
                        [{**ok_entry, "focus_equivalent": None}], html)
        ok, _ = run(*g)
        cases.append(("负向夹具5：缺焦点等价面（期望 FAIL）", not ok))

        # ★ 批十三 新增判据（decor kind ＋ 属性选择器 C2）的负向/对照夹具
        decor_entry = {
            "selector": "[data-spotlight]:hover::before", "kind": "decor",
            "hotspot": "[data-spotlight]", "coverage_min": None,
            "focus_equivalent": None, "status": "ok", "reason": "夹具",
        }
        css_decor = FIXTURE_CSS_OK + (
            "\n@media (hover: hover) {\n  [data-spotlight]:hover::before { opacity: 1; }\n}\n")
        html_decor = html + '<article class="card" data-spotlight="base"><a href="/z">x</a></article>'
        h = _mk_fixture(tmp / "decor-ok", css_decor, [ok_entry, decor_entry], html_decor)
        ok, _ = run(*h)
        cases.append(("★批十三 对照臂：decor 豁免 C3/C4 ＋ 属性选择器 hotspot 可命中（期望 PASS）", ok))

        # 负向夹具 6：登记了装饰面，但产物里**没有** `[data-spotlight]` 元素（登记表腐化）
        #   ⇒ 判据须靠**属性存在性**抓住它（改前 compound_hits 不认属性 ⇒ 此处会假 PASS）
        i = _mk_fixture(tmp / "decor-rot", css_decor, [ok_entry, decor_entry], html)
        ok, _ = run(*i)
        cases.append(("★批十三 负向夹具6：产物无 `[data-spotlight]` ⇒ 属性探针零命中（期望 FAIL）", not ok))

        # 负向夹具 7：decor 无法成为「万能逃生门」—— 幽灵登记（CSS 里没有该装饰规则）仍须 FAIL
        j = _mk_fixture(tmp / "decor-ghost", FIXTURE_CSS_OK, [ok_entry, decor_entry], html_decor)
        ok, _ = run(*j)
        cases.append(("★批十三 负向夹具7：decor 幽灵登记（CSS 无对应规则）（期望 FAIL）", not ok))

    print("\n== selftest ==")
    for name, passed in cases:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    all_ok = all(p for _, p in cases)
    print("  SELFTEST:", "PASS" if all_ok else "FAIL（判据可能恒真或恒假）")
    return 0 if all_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="交互作用面门控（反馈面 ≡ 热区）")
    ap.add_argument("--selftest", action="store_true", help="跑负向夹具（含期望 FAIL 的样本）")
    ap.add_argument("--css", type=Path, default=CSS_PATH)
    ap.add_argument("--table", type=Path, default=TABLE_PATH)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.css.exists() or not args.table.exists():
        print("[用法错误] 缺 CSS 或声明表；先确认路径（或先 pnpm build 生成 out/）")
        return 2
    if not args.out.exists():
        print("[用法错误] out/ 不存在 —— 本门控读真实产物，请先 pnpm build")
        return 2
    ok, _ = run(args.css, args.table, args.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
