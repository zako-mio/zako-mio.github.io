#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""登记完整性机检：scripts/probes/ 下每个 `*_probe.py` 活件都必须在 PROVENANCE.json 登记。

判据（fail-closed；任一条不成立即 rc=1）：
  P1 **无漏登记**：`scripts/probes/*_probe.py` 的每个文件都在 `probes[].repo` 里出现；
  P2 **无幽灵登记**：`probes[].repo` 指向的文件都存在；
  P3 **字段齐备**：每条登记都带 origin / requires / needs_server / selftest，且 origin 取值合法；
      `origin == "archive-copy"` 者还须带 archive_source / copied_from_commit / source_sha256(64 hex)；
  P4 **非空**（逃亡门守卫）：登记表与目录扫描**都不得**为空 —— 空集不得静默通过。

★ 为什么需要这一条：来源登记若只写在散文里（或写了个空表），会随新增探针静默失效。
  这是「登记完整性本身须被看住」的机检落点（与 gate_ia_division 的 A7/A8 同型）。

⚠ **声明的不覆盖面**：本检只判「登记表 ↔ 目录」的**对应关系**；⛔ 不校验 source_sha256 是否
   真等于归档件的字节摘要（归档不在仓库内、CI 不可达）—— 那一段只能人工/离线复算。

用法：
    python3 scripts/probes/check_provenance.py
    python3 scripts/probes/check_provenance.py --selftest     # 临时夹具，验证判据非恒真
    python3 scripts/probes/check_provenance.py --root <dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBES_DIR = "scripts/probes"
PROVENANCE = "scripts/probes/PROVENANCE.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def check(root: Path) -> list[str]:
    problems: list[str] = []
    prov_path = root / PROVENANCE
    if not prov_path.exists():
        return [f"P{1} 登记表不存在：{PROVENANCE}"]

    try:
        data = json.loads(prov_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"登记表不可解析：{exc}"]

    entries = data.get("probes")
    if not isinstance(entries, list):
        return ["登记表缺 probes 数组"]

    declared = [e.get("repo", "") for e in entries]
    actual = sorted(str(p.relative_to(root)) for p in (root / PROBES_DIR).glob("*_probe.py"))

    if not actual:
        problems.append("P4 目录扫描为空（scripts/probes 下无 *_probe.py）—— 判据在此哑火，⛔ 不得静默通过")
    if not declared:
        problems.append("P4 登记表为空 —— 判据在此哑火，⛔ 不得静默通过")

    # P1 漏登记
    for a in sorted(set(actual) - set(declared)):
        problems.append(f"P1 漏登记：{a} 在目录中但未登记进 PROVENANCE.json")
    # P2 幽灵登记
    for d in sorted(set(declared) - set(actual)):
        problems.append(f"P2 幽灵登记：{d} 已登记但文件不存在")
    # P3 字段齐备
    for e in entries:
        repo = e.get("repo", "<无 repo 字段>")
        for field in ("origin", "requires", "needs_server", "selftest"):
            if field not in e:
                problems.append(f"P3 {repo} 缺字段 {field}")
        origin = e.get("origin")
        if origin not in ("archive-copy", "repo-native"):
            problems.append(f"P3 {repo} origin 非法（应为 archive-copy / repo-native）：{origin!r}")
        if origin == "archive-copy":
            for field in ("archive_source", "copied_from_commit", "source_sha256"):
                if field not in e:
                    problems.append(f"P3 {repo}（archive-copy）缺字段 {field}")
            if not SHA256_RE.match(str(e.get("source_sha256", ""))):
                problems.append(f"P3 {repo} source_sha256 非法（应为 64 位小写 hex）")
    return problems


# ---------------------------------------------------------------- selftest
def selftest() -> int:
    checks: list[tuple[str, bool]] = []

    def make(root: Path, probe_files: list[str], declared: list[str]) -> None:
        d = root / PROBES_DIR
        d.mkdir(parents=True, exist_ok=True)
        for f in probe_files:
            (d / f).write_text("# fixture\n", encoding="utf-8")
        entry = {"origin": "archive-copy", "archive_source": "x/y.py", "copied_from_commit": "abc",
                 "source_sha256": "0" * 64, "requires": [], "needs_server": False, "selftest": True}
        (root / PROVENANCE).write_text(
            json.dumps({"probes": [{"repo": r, **entry} for r in declared]}), encoding="utf-8")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # 负例 1：漏登记
        make(root, ["a_probe.py", "b_probe.py"], ["scripts/probes/a_probe.py"])
        p = check(root)
        checks.append(("负向夹具：漏登记 b_probe.py 被抓到", any("P1" in x and "b_probe" in x for x in p)))
        # 负例 2：幽灵登记
        make(root, ["a_probe.py"], ["scripts/probes/a_probe.py", "scripts/probes/gone_probe.py"])
        p = check(root)
        checks.append(("负向夹具：幽灵登记 gone_probe.py 被抓到", any("P2" in x and "gone_probe" in x for x in p)))
        # 负例 3：空集
        make(root, [], [])
        p = check(root)
        checks.append(("负向夹具：空集（无探针 + 空表）被抓到", any("P4" in x for x in p)))
        # 负例 4：非法 sha256
        make(root, ["a_probe.py"], ["scripts/probes/a_probe.py"])
        (root / PROVENANCE).write_text(json.dumps({"probes": [
            {"repo": "scripts/probes/a_probe.py", "origin": "archive-copy", "archive_source": "x",
             "copied_from_commit": "c", "source_sha256": "NOTHEX", "requires": [],
             "needs_server": False, "selftest": True}]}), encoding="utf-8")
        p = check(root)
        checks.append(("负向夹具：非法 sha256 被抓到", any("P3" in x and "sha256" in x for x in p)))
        # 负例 5：archive-copy 缺归档字段 / origin 非法
        (root / PROVENANCE).write_text(json.dumps({"probes": [
            {"repo": "scripts/probes/a_probe.py", "origin": "archive-copy", "requires": [],
             "needs_server": False, "selftest": True}]}), encoding="utf-8")
        p = check(root)
        checks.append(("负向夹具：archive-copy 缺 archive_source/sha256 被抓到",
                       any("P3" in x and "archive_source" in x for x in p)
                       and any("P3" in x and "sha256" in x for x in p)))
        (root / PROVENANCE).write_text(json.dumps({"probes": [
            {"repo": "scripts/probes/a_probe.py", "origin": "unknown-x", "requires": [],
             "needs_server": False, "selftest": True}]}), encoding="utf-8")
        p = check(root)
        checks.append(("负向夹具：origin 非法取值被抓到", any("origin 非法" in x for x in p)))
        # 对照臂：合规基线
        make(root, ["a_probe.py", "b_probe.py"],
             ["scripts/probes/a_probe.py", "scripts/probes/b_probe.py"])
        p = check(root)
        checks.append(("对照臂：合规基线零问题", not p))

    print("== selftest（临时夹具；⛔ 不改仓库）==")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    good = all(ok for _, ok in checks)
    print("  SELFTEST:", "PASS" if good else "FAIL（判据可能恒真）")
    return 0 if good else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="scripts/probes 来源登记完整性机检")
    ap.add_argument("--root", type=Path, default=REPO_ROOT, help=f"仓库根（缺省 {REPO_ROOT}）")
    ap.add_argument("--selftest", action="store_true", help="临时夹具，验证判据非恒真")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    problems = check(args.root.resolve())
    if problems:
        for p in problems:
            print(f"  [FAIL] {p}")
        print(f"\nPROVENANCE: HAS FAILURE ({len(problems)})")
        return 1
    n = len(json.loads((args.root.resolve() / PROVENANCE).read_text(encoding="utf-8"))["probes"])
    print(f"  [PASS] 登记完整：{n} 条探针全部登记，无漏登记 / 无幽灵登记 / 字段齐备 / 非空")
    print("\nPROVENANCE: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
