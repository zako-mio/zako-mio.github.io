#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E1：CI workflow ↔ 登记集合 **一致性机检**（fail-closed）。

背景（本站反复踩的坑，见 README「probes」节 ★）：CI 的步骤是**逐条手列**的，
不会自动跟随任何 manifest ⇒ **「已登记」≠「已进 CI」**。实测缺口：`acceptance_probe.py` /
`dup_probe.py` 早已登记进 `PROVENANCE.json`，却**从未进 CI**，且**没有任何判据能发现**这件事
（静默缺口 —— 与「判据的空白面会长期掩盖既有缺陷」同型）。

本机检把该缺口做成 fail-closed，判据对象＝**三个真相源的两两一致性**：
  W = `.github/workflows/update-hub.yml`   （谁在 CI 里跑 —— 逐条列举）
  M = `scripts/gate-manifest.json`          （门控登记；`scripts/` 内门控不漏登记由 A8 保证）
  P = `scripts/probes/PROVENANCE.json`      （探针登记；目录不漏登记由 check_provenance.py 保证）

| id | 判据 | 目标 |
|----|------|------|
| E1-1 | **门控覆盖**：M 里每道门控都在 W 里被调用 | 差集为空 |
| E1-2 | **门控反向**：W 里出现的 `gate_*.py`/`smoke_*.py` 必须在 M 登记（无幽灵 CI 步骤） | 差集为空 |
| E1-3 | **探针覆盖**：P 里每个探针都在 W 里被调用 | 差集为空 |
| E1-4 | **探针反向**：W 里出现的 `*_probe.py` 必须在 P 登记 | 差集为空 |
| E1-5 | **非空守卫**：W/M/P 取出的集合都不得为空（空集不得静默通过） | 均非空 |

★ 设计取舍：**不设「豁免/白名单」**——豁免是逃逸门，会把「静默缺口」换成「显式豁免」而非消除它。
  本站接受「登记即进 CI 义务」这条更强口径（与 A8 的「命名约定即登记义务」同构）。
  ⇒ 新探针/新门控若**不能**进 CI，正确做法是**不要登记**（或另行裁决），⛔ 不是加白名单。

⚠ 声明的不覆盖面：
  ① 本检只判「集合一致性」；⛔ 不判 CI 步骤的**顺序/依赖**（如「须在 build 之后」）是否成立。
  ② 抽取 CI 脚本用**正则**（`python3 <路径>.py`）⇒ 若将来改用别的调用形态（Makefile / action 封装），
     本检会**哑火**（抽出集合变小）。E1-5 的非空守卫只能兜住「全空」，兜不住「部分漏抽」。
     故：**改 CI 调用形态时须同批复核本正则**。
  ③ ⛔ 不判 `scripts/cli.py` / `validate_catalog.py` / `collect_metrics.py` 这类**流水线脚本**
     （非门控、非探针）—— 它们不在 M/P 的登记面内。

用法：
    python3 scripts/check_ci_manifest.py
    python3 scripts/check_ci_manifest.py --selftest     # 临时夹具，证明判据非恒真
    python3 scripts/check_ci_manifest.py --root <dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ".github/workflows/update-hub.yml"
MANIFEST = "scripts/gate-manifest.json"
PROVENANCE = "scripts/probes/PROVENANCE.json"

# CI 里调用 python 脚本的形态（当前：`python3 scripts/...py`）。捕获组＝脚本路径。
CI_PY = re.compile(r"python3\s+([^\s'\"]+\.py)")
GATE_RE = re.compile(r"^(gate_|smoke_).*\.py$")
PROBE_RE = re.compile(r"_probe\.py$")


def _extract_ci_scripts(text: str) -> set[str]:
    return {m.group(1).strip() for m in CI_PY.finditer(text)}


def check(root: Path) -> list[str]:
    problems: list[str] = []

    wf_path = root / WORKFLOW
    man_path = root / MANIFEST
    prov_path = root / PROVENANCE
    for label, p in ((WORKFLOW, wf_path), (MANIFEST, man_path), (PROVENANCE, prov_path)):
        if not p.exists():
            return [f"{label} 不存在"]

    try:
        wf_text = wf_path.read_text(encoding="utf-8")
        manifest = json.loads(man_path.read_text(encoding="utf-8"))
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"输入不可解析：{exc}"]

    ci = _extract_ci_scripts(wf_text)
    gates = [g.get("script", "") for g in manifest.get("gates", [])]
    probes = [e.get("repo", "") for e in prov.get("probes", [])]

    # E1-5 非空守卫
    if not ci:
        problems.append("E1-5 CI 脚本集合为空（正则未抽到任何 `python3 *.py`）—— 判据在此哑火，⛔ 不得静默通过")
    if not gates:
        problems.append("E1-5 门控登记集合为空")
    if not probes:
        problems.append("E1-5 探针登记集合为空")

    # E1-1 门控覆盖：登记 ⇒ 必须进 CI
    for g in sorted(set(gates) - ci):
        problems.append(f"E1-1 门控漏进 CI：{g} 已登记进 gate-manifest.json，但 update-hub.yml 未调用")

    # E1-2 门控反向：CI 里的门控 ⇒ 必须登记
    ci_gates = {s for s in ci if GATE_RE.match(Path(s).name)}
    for g in sorted(ci_gates - set(gates)):
        problems.append(f"E1-2 幽灵 CI 门控：{g} 在 update-hub.yml 中调用，但未登记进 gate-manifest.json")

    # E1-3 探针覆盖：登记 ⇒ 必须进 CI
    for p in sorted(set(probes) - ci):
        problems.append(f"E1-3 探针漏进 CI：{p} 已登记进 PROVENANCE.json，但 update-hub.yml 未调用")

    # E1-4 探针反向：CI 里的探针 ⇒ 必须登记
    ci_probes = {s for s in ci if PROBE_RE.search(Path(s).name)}
    for p in sorted(ci_probes - set(probes)):
        problems.append(f"E1-4 幽灵 CI 探针：{p} 在 update-hub.yml 中调用，但未登记进 PROVENANCE.json")

    return problems


# ---------------------------------------------------------------- selftest
def _write_fixture(root: Path, ci_scripts: list[str], gates: list[str], probes: list[str]) -> None:
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "probes").mkdir(parents=True, exist_ok=True)
    lines = ["name: fixture", "on: [workflow_dispatch]", "jobs:", "  build:", "    runs-on: ubuntu-latest",
             "    steps:"]
    for s in ci_scripts:
        lines.append(f"      - run: python3 {s}")
    (root / WORKFLOW).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / MANIFEST).write_text(json.dumps({"gates": [{"script": g} for g in gates]}), encoding="utf-8")
    (root / PROVENANCE).write_text(json.dumps({"probes": [{"repo": p} for p in probes]}), encoding="utf-8")


def selftest() -> int:
    checks: list[tuple[str, bool]] = []

    def probe(ci_scripts, gates, probes):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_fixture(root, ci_scripts, gates, probes)
            return check(root)

    # 对照臂：完全一致 ⇒ 零问题
    p = probe(["scripts/gate_a.py", "scripts/probes/x_probe.py"],
              ["scripts/gate_a.py"], ["scripts/probes/x_probe.py"])
    checks.append(("对照臂：登记与 CI 完全一致 ⇒ 零问题", not p))

    # E1-1 门控漏进 CI
    p = probe(["scripts/gate_a.py", "scripts/probes/x_probe.py"],
              ["scripts/gate_a.py", "scripts/gate_b.py"], ["scripts/probes/x_probe.py"])
    checks.append(("负向夹具 E1-1：门控 gate_b.py 漏进 CI 被抓到",
                   any("E1-1" in x and "gate_b.py" in x for x in p)))

    # E1-2 幽灵 CI 门控
    p = probe(["scripts/gate_a.py", "scripts/gate_ghost.py"],
              ["scripts/gate_a.py"], [])
    checks.append(("负向夹具 E1-2：CI 里的 gate_ghost.py 未登记被抓到",
                   any("E1-2" in x and "gate_ghost" in x for x in p)))

    # E1-3 探针漏进 CI
    p = probe(["scripts/probes/x_probe.py"],
              [], ["scripts/probes/x_probe.py", "scripts/probes/y_probe.py"])
    checks.append(("负向夹具 E1-3：探针 y_probe.py 已登记却未进 CI 被抓到",
                   any("E1-3" in x and "y_probe" in x for x in p)))

    # E1-4 幽灵 CI 探针
    p = probe(["scripts/probes/ghost_probe.py"], [], ["scripts/probes/x_probe.py"])
    checks.append(("负向夹具 E1-4：CI 里的 ghost_probe.py 未登记被抓到",
                   any("E1-4" in x and "ghost_probe" in x for x in p)))

    # E1-5 空集
    p = probe([], [], [])
    checks.append(("负向夹具 E1-5：空集（CI/门控/探针全空）被抓到", any("E1-5" in x for x in p)))

    print("== selftest（临时夹具；⛔ 不改仓库）==")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    good = all(ok for _, ok in checks)
    print("  SELFTEST:", "PASS" if good else "FAIL（判据可能恒真）")
    return 0 if good else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="CI workflow ↔ 登记集合 一致性机检（E1）")
    ap.add_argument("--root", type=Path, default=REPO_ROOT, help=f"仓库根（缺省 {REPO_ROOT}）")
    ap.add_argument("--selftest", action="store_true", help="临时夹具，验证判据非恒真")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    problems = check(args.root.resolve())
    if problems:
        for p in problems:
            print(f"  [FAIL] {p}")
        print(f"\nCI-MANIFEST: HAS FAILURE ({len(problems)})")
        return 1
    root = args.root.resolve()
    n_g = len(json.loads((root / MANIFEST).read_text(encoding="utf-8"))["gates"])
    n_p = len(json.loads((root / PROVENANCE).read_text(encoding="utf-8"))["probes"])
    print(f"  [PASS] CI↔登记一致：{n_g} 道门控 + {n_p} 条探针全部进 CI，无幽灵步骤，集合非空")
    print("\nCI-MANIFEST: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
