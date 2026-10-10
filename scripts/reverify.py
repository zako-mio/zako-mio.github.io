#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日常复验器（B8）· 把第三批新增手法固化为**可执行**的常规复验。

设计纪律（见 README「日常复验」）：
  - 只读 + 可重跑；⛔ 不复读任何历史记录/自述，一切读数当场重算；
  - fail-closed：任一判据 FAIL ⇒ 退出码非零；
  - 本器**不是门控**（不进 `scripts/gate-manifest.json`），而是编排既有门控/派生器/探针的入口。

覆盖（对应 START-PROMPT-BATCH4 §4 G2 的 ①–⑤）：
  S1 门控与自检：清单在案的每道门控跑「本体 ＋ --selftest」，两者 rc 必须为 0
  S2 派生件跨进程幂等：charts / topology 各**两个独立进程**重建，剔除运行时钟字段后逐字节一致
  S3 数字类断言全量对账：跨产物计数一致性 ＋ topology↔metrics 复算 ＋ 上游层次口径共指纹 ＋ 产物渲染断言
  S4 判据自检覆盖：每道声明 `selftest:true` 的门控，其自检输出**必须含负向夹具触发证据**（⛔ 不是恒真）
  S5 探针复跑：acceptance_probe（结构类，须 ALL PASS）＋ dup_probe（数值/报告类，只须可跑）

用法：
    pnpm build && python3 scripts/reverify.py            # 完整复验
    python3 scripts/reverify.py --skip S2,S5             # 跳过慢/联网段
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
NODE = "node"

RESULTS: list[tuple[str, str, str]] = []


def record(section: str, ok: bool, msg: str) -> None:
    RESULTS.append((section, "PASS" if ok else "FAIL", msg))
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


VOLATILE = {"metrics_as_of", "as_of", "generated_at", "fetched_at"}


def normalize(obj):
    if isinstance(obj, dict):
        return {k: normalize(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [normalize(v) for v in obj]
    return obj


COMMENT = re.compile(r"<!--.*?-->", re.S)
WS = re.compile(r"\s+")


def visible_html(path: Path) -> str:
    """读产物 HTML 并归一化：剥注释（React 会在相邻文本节点间插入 `<!-- -->`）、压空白。

    ⚠ 这是**测尺子自身**的修正：产物里「19<!-- --> 层」若不做归一，会被误判为未呈现「19 层」。
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    return WS.sub(" ", COMMENT.sub(" ", raw))


TOPO_ITEM_OPEN = re.compile(r'<li class="topo__item"[^>]*>')


def _li_slice(text: str, start: int) -> str:
    """从 `start`（某个 `<li>` 的起点）切到与之**配对**的 `</li>`（按嵌套计数）。"""
    depth = 0
    for m in re.finditer(r"<li\b|</li>", text[start:]):
        depth += 1 if m.group(0) == "<li" else -1
        if depth == 0:
            return text[start : start + m.end()]
    return text[start:]


def topo_items(text: str) -> list[str]:
    """切出每个图谱项（`<li class="topo__item">`）**自身**的 HTML 片段。

    ★ 为什么必须切块（批十四 W2 实测到的假 FAIL）：C5/C6 原来以**整页**文本搜
      「不可判定」，而本批新增的**术语解释层**（`.term__def`，通用词条文本）恰好含这四个字
      ⇒ 页面无端被判「仍显示不可判定」。判据作用面必须 = 被判对象（该图谱项的渲染结果）。
    """
    return [_li_slice(text, m.start()) for m in TOPO_ITEM_OPEN.finditer(text)]


# ────────────────────────────── S1 / S4 ──────────────────────────────

NEGATIVE_EVIDENCE = re.compile(r"期望 FAIL|被抓到|负向样本|负向夹具")


def section_gates(manifest: dict) -> None:
    print("\n== S1 门控与自检（清单在案的门控，本体 ＋ --selftest）==")
    for gate in manifest.get("gates", []):
        script = gate["script"]
        base = run([PY, script])
        record("S1", base.returncode == 0, f"{script} → rc={base.returncode}")
        if not gate.get("selftest"):
            continue
        st = run([PY, script, "--selftest"])
        out = st.stdout + st.stderr
        record("S1", st.returncode == 0, f"{script} --selftest → rc={st.returncode}")
        if st.returncode != 0:
            print(f"      …输出尾部：{out.strip()[-300:]}")
    manifest_gates = {g["script"] for g in manifest.get("gates", [])}
    on_disk = sorted(
        str(p.relative_to(ROOT))
        for p in (ROOT / "scripts").glob("gate_*.py")
    ) + sorted(
        str(p.relative_to(ROOT))
        for p in (ROOT / "scripts").glob("smoke_*.py")
    )
    missing = [s for s in on_disk if s not in manifest_gates]
    record("S1", not missing, f"命名约定内门控全部登记（未登记：{missing or '无'}）")


def section_selftest_evidence(manifest: dict) -> None:
    print("\n== S4 判据自检覆盖（自检须含负向夹具触发证据，⛔ 恒真即 FAIL）==")
    for gate in manifest.get("gates", []):
        if not gate.get("selftest"):
            record("S4", False, f"{gate['script']} 声明 selftest:false —— 判据须内置负向夹具")
            continue
        st = run([PY, gate["script"], "--selftest"])
        out = st.stdout + st.stderr
        has_positive = bool(re.search(r"对照臂|基线|期望 PASS", out)) or "SELFTEST" in out
        has_negative = bool(NEGATIVE_EVIDENCE.search(out))
        record("S4", st.returncode == 0 and has_negative,
               f"{gate['script']} 自检含负向夹具证据={has_negative} 对照臂线索={has_positive}")


# ────────────────────────────── S2 ──────────────────────────────

def section_derived_idempotent() -> None:
    print("\n== S2 派生件跨进程幂等（charts / topology，两次独立进程重建）==")
    specs = [
        ("charts", NODE, "scripts/build_charts.mjs", "--out"),
        ("topology", NODE, "scripts/build_topology.mjs", "--out"),
    ]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for name, exe, script, flag in specs:
            a, b = td / f"{name}.a.json", td / f"{name}.b.json"
            r1 = run([exe, script, flag, str(a)])
            r2 = run([exe, script, flag, str(b)])
            if r1.returncode != 0 or r2.returncode != 0:
                record("S2", False, f"{script} 重建失败 rc={r1.returncode}/{r2.returncode}")
                continue
            try:
                ja, jb = json.loads(a.read_text(encoding="utf-8")), json.loads(b.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                record("S2", False, f"{script} 产物不可解析：{exc}")
                continue
            same = normalize(ja) == normalize(jb)
            record("S2", same, f"{script} 两次跨进程重建{'逐字节一致（剔除时钟字段）' if same else '不一致'}")

            # 幂等：同路径二次运行不得产生差异
            r3 = run([exe, script, flag, str(a)])
            ja2 = json.loads(a.read_text(encoding="utf-8"))
            record("S2", r3.returncode == 0 and normalize(ja) == normalize(ja2),
                   f"{script} 同路径二次运行幂等={r3.returncode == 0 and normalize(ja) == normalize(ja2)}")


# ────────────────────────────── S3 ──────────────────────────────

def section_numeric_reconcile() -> None:
    print("\n== S3 数字类断言全量对账（当场重算，⛔ 不复读记录）==")
    try:
        projects = load_json("src/data/projects.json")["projects"]
        metrics = load_json("src/data/metrics.json")
        topology = load_json("src/data/topology.json")
        charts = load_json("src/data/charts.json")
    except FileNotFoundError as exc:
        record("S3", False, f"缺产物：{exc}（先跑数据链路与 build）")
        return

    # C1 跨产物计数一致
    P = len(projects)
    T = metrics.get("project_total")
    M = len(metrics.get("projects", []))
    counts = metrics.get("counts", {})
    O, U, F = counts.get("ok"), counts.get("unavailable"), counts.get("fetch_failures")
    ok_n = sum(1 for p in metrics.get("projects", []) if p.get("status") == "ok")
    un_n = sum(1 for p in metrics.get("projects", []) if p.get("status") == "unavailable")
    record("S3", P == T == M, f"项目数一致：projects.json={P} · metrics.project_total={T} · metrics.projects={M}")
    record("S3", O == ok_n and U == un_n, f"状态计数一致：ok {O}/{ok_n} · unavailable {U}/{un_n}")
    record("S3", (O or 0) + (U or 0) + (F or 0) == T, f"ok+unavailable+fetch_failures={ (O or 0)+(U or 0)+(F or 0) } == total {T}")

    # C2 状态词表 + unavailable 必须给出理由（⛔ 不得静默跳过）
    bad = [p.get("name") for p in metrics.get("projects", []) if p.get("status") not in {"ok", "unavailable", "fetch_failed"}]
    record("S3", not bad, f"状态词表合法（越界：{bad or '无'}）")
    no_note = [p.get("name") for p in metrics.get("projects", []) if p.get("status") == "unavailable" and not p.get("notes")]
    record("S3", not no_note, f"unavailable 均带理由（缺失：{no_note or '无'}）")

    # C3 topology ↔ metrics 复算（两份定义不得漂移）
    declared = {(e["name"], f["scope"]): f for e in metrics.get("projects", []) for f in e.get("figures", [])}
    drift = []
    for g in topology.get("graphs", []):
        fig = declared.get((g["project"], g["scope"]))
        if fig is None:
            drift.append(f"{g['project']}/{g['scope']}: metrics 无对应 scope")
            continue
        if fig.get("entity_count") is not None and fig["entity_count"] != g["analysis"]["node_count"]:
            drift.append(f"{g['project']}/{g['scope']}: 节点 {g['analysis']['node_count']} ≠ 登记 {fig['entity_count']}")
        if fig.get("relation_count") is not None and fig["relation_count"] != g["analysis"]["edge_count"]:
            drift.append(f"{g['project']}/{g['scope']}: 边 {g['analysis']['edge_count']} ≠ 登记 {fig['relation_count']}")
    record("S3", not drift, f"topology↔metrics 复算一致（漂移：{drift or '无'}）")

    # C4 上游层次口径共指纹（G3 回归护栏，2026-10-08 新增）
    parity_fail = []
    for g in topology.get("graphs", []):
        par = g["analysis"].get("upstream_layer_parity")
        if par and par.get("mismatches", 0) > 0:
            parity_fail.append(f"{g['scope']}: {par['mismatches']}/{par['compared']} 不一致 · {par.get('sample')}")
    record("S3", not parity_fail, f"上游层次口径共指纹一致（不符：{parity_fail or '无'}）")

    # C5/C6 产物渲染断言（读真实 out/）
    out = ROOT / "out"
    if not out.exists():
        record("S3", False, "out/ 不存在（先 pnpm build）")
        return
    missing_pages = [p["name"] for p in projects if not (out / "works" / p["name"] / "index.html").exists()]
    record("S3", not missing_pages, f"每个项目详情页已生成（缺失：{missing_pages or '无'}）")

    render_issues = []
    for g in topology.get("graphs", []):
        page = out / "works" / g["project"] / "index.html"
        if not page.exists():
            continue
        h = visible_html(page)
        a = g["analysis"]
        if g["scope"] not in h:
            render_issues.append(f"{g['project']}/{g['scope']}: 页面未呈现 scope")
        # ★ 断言**只在该图谱项自身**的渲染块内做（⛔ 不用整页文本 —— 会被术语解释层等
        #   通用文本污染成假 FAIL，见 `topo_items()` 的说明）。
        block = next((b for b in topo_items(h) if g["scope"] in b), None)
        if block is None:
            render_issues.append(f"{g['project']}/{g['scope']}: 未找到该项的 topo__item 渲染块")
            continue
        if a["acyclic"] and a["longest_path_layers"] is not None:
            if f"{a['longest_path_layers']} 层" not in block:
                render_issues.append(f"{g['project']}/{g['scope']}: 页面未呈现「{a['longest_path_layers']} 层」")
            if "不可判定" in block:
                render_issues.append(f"{g['project']}/{g['scope']}: 页面仍显示「不可判定」")
        if g.get("agreement", {}).get("acyclic") is True and "与独立复算一致" not in block:
            render_issues.append(f"{g['project']}/{g['scope']}: 未呈现「与独立复算一致」")
    record("S3", not render_issues, f"图谱渲染断言通过（问题：{render_issues or '无'}）")

    # C7 charts 结构自洽（⛔ 键名以产物真实书写形态为准，非构建器 stdout 摘要）
    chart_list = charts.get("charts", [])
    bad_charts = [
        c.get("key")
        for c in chart_list
        if not (c.get("svg", {}) or {}).get("light") or not (c.get("svg", {}) or {}).get("dark")
    ]
    record("S3", not bad_charts, f"每张图双模 SVG 均非空（空：{bad_charts or '无'}）；图表数={len(chart_list)}")


# ────────────────────────────── S5 ──────────────────────────────

def section_probes() -> None:
    print("\n== S5 探针复跑（结构类须 ALL PASS；报告类只须可跑）==")
    ap = run([PY, "scripts/probes/acceptance_probe.py"])
    record("S5", ap.returncode == 0, f"acceptance_probe（结构类）→ rc={ap.returncode} · {ap.stdout.strip().splitlines()[-1] if ap.stdout.strip() else ''}")
    dp = run([PY, "scripts/probes/dup_probe.py"])
    ran = dp.returncode == 0 and "页间块级重合" in dp.stdout
    record("S5", ran, f"dup_probe（数值/报告类）可跑={ran}（⛔ 重合度不判 PASS/FAIL）")
    if ran:
        for line in dp.stdout.splitlines():
            if line.strip().startswith(("首页 /", "作品 /works", "聚合 /stats", "关于 /about")):
                print(f"      {line.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", default="", help="逗号分隔：跳过 S1..S5 中的某几段")
    args = ap.parse_args()
    skip = {s.strip().upper() for s in args.skip.split(",") if s.strip()}

    manifest = load_json("scripts/gate-manifest.json")
    print(f"== 日常复验 reverify · repo={ROOT} · 跳过={sorted(skip) or '无'} ==")

    if "S1" not in skip:
        section_gates(manifest)
    if "S2" not in skip:
        section_derived_idempotent()
    if "S3" not in skip:
        section_numeric_reconcile()
    if "S4" not in skip:
        section_selftest_evidence(manifest)
    if "S5" not in skip:
        section_probes()

    fails = [r for r in RESULTS if r[1] == "FAIL"]
    print(f"\n{'=' * 60}")
    print(f"REVERIFY: {len(RESULTS) - len(fails)}/{len(RESULTS)} PASS"
          + (f" · FAIL {len(fails)} 条" if fails else " · ALL PASS"))
    for _, _, msg in fails:
        print(f"  ✗ {msg}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
