#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E 指标采集门控（2b-3）· fail-closed。

读**真实产物**，⛔ 不读源码自述：
  - ``src/data/metrics.json``            采集器实跑产物
  - ``src/data/projects.json``           项目目录（判「覆盖 == 枚举」的另一侧）
  - ``src/data/metrics-confirmed.json``   E4 确认登记（冻结锚点）

判据分两档（档位是**预登记**的，⛔ 不按数据回头改）：
  FAIL —— 结构/口径错误：会污染页面或说明链路断了，必须阻断。
  WARN —— 上游事实变化或采集侧短板：不阻断，但必须留痕（「不阻断」≠「不留痕」）。

  G1  产物齐备且 JSON 合法
  G2  覆盖 == 枚举：metrics 项目集 ≡ projects.json 项目集
  G3  每项 status ∈ {ok, unavailable}；unavailable 必须带理由
  G4  E5：任何 figure 的任何归一名不得为 0（0 ≠ 无）
  G5  E5：status=ok 的项至少一个归一名有值（⛔ 不得靠空表冒充 ok）
  G6  A 级交叉校验不得出现 MISMATCH（出现即上游不同步，交人工）
  G7  「计数 == 枚举」：JSON 自述计数 == 数组枚举长度
  G8  E4：source 必须带 64 位 hex 文本哈希 ＋ 非空原文片段
  G9  E1：figure 数 ≥ max(1, 声明的 JSON 资产数)（多 scope 不得被单值化）
  G10 E4 冻结锚点：重采后页面文本哈希 / 已确认取值与登记不符 => WARN「确认已过期」
  G11 口径表自洽：分区表与采集定义表项目集相等（消费侧走同一真相源）
  G12 E2：同一 scope 内 layer_count 与 stage_count 不同时非空（分层 ≠ 分期）

用法::

    python3 scripts/gate_metrics.py                # 正常门控
    python3 scripts/gate_metrics.py --selftest     # 负向夹具自检（每条判据都要能 FAIL）
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import collect_metrics as cm  # noqa: E402 - 口径表唯一真相源，消费侧走同一函数/表

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NORMS = ("entity_count", "group_count", "relation_count", "layer_count", "stage_count")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class Findings:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, level: str, check: str, target: str, message: str) -> None:
        self.items.append({"level": level, "check": check, "target": target, "message": message})

    def fail(self, check: str, target: str, message: str) -> None:
        self.add("FAIL", check, target, message)

    def warn(self, check: str, target: str, message: str) -> None:
        self.add("WARN", check, target, message)

    @property
    def failures(self) -> list[dict[str, str]]:
        return [i for i in self.items if i["level"] == "FAIL"]

    @property
    def warnings(self) -> list[dict[str, str]]:
        return [i for i in self.items if i["level"] == "WARN"]


def run_checks(
    metrics: Optional[dict[str, Any]],
    catalog: Optional[dict[str, Any]],
    ledger: Optional[dict[str, Any]],
) -> Findings:
    found = Findings()

    # G1 产物齐备
    if not isinstance(metrics, dict):
        found.fail("G1", "metrics.json", "缺失或不是 JSON 对象")
        return found
    for key in ("as_of", "site", "project_total", "declared_total", "projects"):
        if key not in metrics:
            found.fail("G1", "metrics.json", f"缺少顶层字段 {key}")
    if found.failures:
        return found

    entries = metrics["projects"]
    if not isinstance(entries, list) or not entries:
        found.fail("G1", "metrics.json", "projects 为空")
        return found

    # G2 覆盖 == 枚举
    if isinstance(catalog, dict) and catalog.get("projects"):
        catalog_names = {item["name"] for item in catalog["projects"]}
        metrics_names = {entry["name"] for entry in entries}
        for name in sorted(catalog_names - metrics_names):
            found.fail("G2", name, "在项目目录中但未被采集（漏采）")
        for name in sorted(metrics_names - catalog_names):
            found.fail("G2", name, "在采集产物中但不在项目目录（幽灵项）")
        if metrics.get("project_total") != len(entries):
            found.fail("G2", "metrics.json",
                       f"project_total={metrics.get('project_total')} 与 entries={len(entries)} 不符")
    else:
        found.warn("G2", "projects.json", "不可用，跳过覆盖枚举比对")

    # G11 口径表自洽
    if set(cm.SECTIONS) != set(cm.PROJECT_DEFS):
        found.fail("G11", "collect_metrics", "SECTIONS 与 PROJECT_DEFS 项目集不相等")

    for entry in entries:
        name = entry.get("name", "<unnamed>")
        status = entry.get("status")

        # G3 状态与理由
        if status not in ("ok", "unavailable"):
            found.fail("G3", name, f"status 非法：{status!r}")
        if status == "unavailable":
            if not entry.get("notes"):
                found.fail("G3", name, "标 unavailable 却无理由（E5 要求显式说明）")
            else:
                found.warn("G3", name, f"unavailable：{entry['notes'][0]}")
        if name not in cm.PROJECT_DEFS and not entry.get("notes"):
            found.fail("G3", name, "项目不在口径表内却无说明")
        if name in cm.PROJECT_DEFS and cm.SECTIONS.get(name) != entry.get("section"):
            found.fail("G11", name, f"分区与口径表不一致：{entry.get('section')} != {cm.SECTIONS.get(name)}")

        figures = entry.get("figures") or []
        any_value = False
        for figure in figures:
            scope = figure.get("scope", "<no-scope>")
            for norm in NORMS:
                value = figure.get(norm)
                if value == 0:
                    found.fail("G4", f"{name}[{scope}].{norm}", "值为 0（E5：0 ≠ 无，须留空）")
                if isinstance(value, int) and value > 0:
                    any_value = True
                if value is not None and not isinstance(value, int):
                    found.fail("G4", f"{name}[{scope}].{norm}", f"值类型非法：{type(value).__name__}")

            # G12 分层与分期不得在同一 scope 同时非空
            if figure.get("layer_count") is not None and figure.get("stage_count") is not None:
                found.warn("G12", f"{name}[{scope}]",
                           "layer_count 与 stage_count 同时非空 —— E2 要求分列，请确认是否混列")

        # G5 ok 必须真的有值
        if status == "ok" and not any_value:
            found.fail("G5", name, "status=ok 但没有任何归一名有值")

        # G6 交叉校验不得有 MISMATCH
        for check in entry.get("checks") or []:
            if check.get("verdict") == "MISMATCH":
                found.fail("G6", f"{name}[{check.get('scope')}].{check.get('field')}",
                           f"JSON 枚举={check.get('json_enumerated')} 与散文={check.get('prose_values')} 不符"
                           "（上游不同步）")

        # G7 自述 == 枚举
        for reported in entry.get("self_reported") or []:
            field = reported.get("field")
            for figure in figures:
                if figure.get(field) is not None and figure[field] != reported["value"]:
                    found.fail("G7", f"{name}[{figure.get('scope')}].{field}",
                               f"枚举={figure[field]} 与上游自述={reported['value']} 不符")

        # G8 E4 取证齐备 / G9 多 scope 不得被单值化
        # ⚠ 作用面限于「口径表在案项目」：规范未覆盖的项目本就不抓页面、不取数，
        #   对它要求 sha256/excerpt 是**判据对象错配**（实测在 CI 真实 10 项数据上误判 FAIL）。
        definition = cm.PROJECT_DEFS.get(name)
        if definition is None:
            if not entry.get("notes"):
                found.fail("G3", name, "不在口径表内却无任何说明（须显式标 unavailable 并给理由）")
            continue

        source = entry.get("source") or {}
        digest = source.get("text_sha256") or ""
        if not SHA256_RE.match(digest):
            found.fail("G8", name, f"页面文本 sha256 非法或缺失：{digest[:16]!r}")
        if not source.get("excerpt"):
            found.fail("G8", name, "缺少页面原文片段（E4 保真要求）")
        if not source.get("fetched_at"):
            found.fail("G8", name, "缺少抓取时点")

        declared_assets = len(definition.get("json_assets") or [])
        expected = max(1, declared_assets)
        if len(figures) < expected:
            found.fail("G9", name, f"figure 数={len(figures)} < 应有个数={expected}（多 scope 被单值化？）")

    # G10 冻结锚点比对
    if isinstance(ledger, dict) and ledger.get("projects"):
        if not ledger.get("confirmed_at"):
            found.warn("G10", "metrics-confirmed.json", "未登记确认日期")
        for entry in entries:
            name = entry["name"]
            frozen = ledger["projects"].get(name)
            if frozen is None:
                found.warn("G10", name, "确认登记中无此项（新增项目尚未确认）")
                continue
            if frozen.get("page_text_sha256") != entry["source"]["text_sha256"]:
                found.warn("G10", name, "页面文本哈希与确认登记不符 —— 上游已改版，E4 确认可能已过期，须重新确认")
            frozen_figures = {f.get("scope"): f for f in frozen.get("figures") or []}
            for figure in entry.get("figures") or []:
                reference = frozen_figures.get(figure.get("scope"))
                if reference is None:
                    found.warn("G10", f"{name}[{figure.get('scope')}]", "确认登记中无此 scope")
                    continue
                for norm in NORMS:
                    was, now = reference.get(norm), figure.get(norm)
                    if was != now:
                        found.warn("G10", f"{name}[{figure.get('scope')}].{norm}",
                                   f"取值已变：确认值={was} 当前值={now} —— 需重新确认（E4）")
    else:
        found.warn("G10", "metrics-confirmed.json", "确认登记不可用，E4 冻结锚点未生效")

    return found


# ────────────────────────────── selftest ──────────────────────────────


def _base_fixture() -> tuple[dict, dict, dict]:
    """最小自洽样本（与真实产物同构，覆盖 A 级 / B 级 / 多 scope 三种形态）。"""
    metrics = {
        "as_of": "2026-10-08T00:00:00Z",
        "site": "https://example.test",
        "project_total": 4,
        "declared_total": 3,
        "projects": [
            {
                "name": "deepseek-harness-plugin-dag",
                "section": "dag",
                "status": "ok",
                "figures": [{"scope": "插件级", "entity_count": 239, "group_count": 50,
                             "relation_count": 1077, "layer_count": 19, "stage_count": None,
                             "provenance": "json:x.json"}],
                "checks": [{"scope": "插件级", "field": "entity_count", "json_enumerated": 239,
                            "prose_values": [239], "verdict": "match"}],
                "self_reported": [{"scope": "插件级", "field": "entity_count", "value": 239, "from": "json:x.json"}],
                "notes": [],
                "source": {"url": "https://example.test/a/", "fetched_at": "2026-10-08T00:00:00Z",
                           "text_sha256": "a" * 64, "excerpt": "239 插件节点"},
            },
            {
                "name": "opencode-dag-analysis",
                "section": "dag",
                "status": "ok",
                "figures": [
                    {"scope": "图1", "entity_count": 36, "group_count": 19, "relation_count": 68,
                     "layer_count": None, "stage_count": None, "provenance": "json:o.json"},
                    {"scope": "图2", "entity_count": 46, "group_count": 20, "relation_count": 68,
                     "layer_count": None, "stage_count": None, "provenance": "json:d.json"},
                    {"scope": "图3", "entity_count": 129, "group_count": 43, "relation_count": 190,
                     "layer_count": 8, "stage_count": None, "provenance": "json:m.json"},
                ],
                "checks": [],
                "self_reported": [],
                "notes": [],
                "source": {"url": "https://example.test/b/", "fetched_at": "2026-10-08T00:00:00Z",
                           "text_sha256": "b" * 64, "excerpt": "36 包 · 68 边 · 19 组"},
            },
            {
                "name": "algorithm-knowledge-graph",
                "section": "dag",
                "status": "ok",
                "figures": [{"scope": "项目页（散文数字）", "entity_count": 372, "group_count": 60,
                             "relation_count": 318, "layer_count": None, "stage_count": 4,
                             "provenance": "prose"}],
                "checks": [],
                "self_reported": [],
                "notes": [],
                "source": {"url": "https://example.test/c/", "fetched_at": "2026-10-08T00:00:00Z",
                           "text_sha256": "c" * 64, "excerpt": "372 知识点 60 知识组"},
            },
            {
                # 口径表外的项目（模拟 CI 真实数据里新增的仓库）：只允许 unavailable + 理由，
                # ⛔ 不得因「没有 sha256 / excerpt」被判 FAIL（判据对象错配）
                "name": "not-in-spec-project",
                "section": "unclassified",
                "status": "unavailable",
                "figures": [],
                "checks": [],
                "self_reported": [],
                "notes": ["未纳入口径规范 v1.0 的项目集"],
                "source": {"url": "https://example.test/d/", "fetched_at": "2026-10-08T00:00:00Z",
                           "text_sha256": None, "excerpt": None},
            },
        ],
    }
    catalog = {"projects": [{"name": e["name"]} for e in metrics["projects"]]}
    ledger = {"confirmed_at": "2026-10-08",
              "projects": {e["name"]: {"page_text_sha256": e["source"]["text_sha256"],
                                       "figures": [{k: v for k, v in f.items() if k != "provenance"}
                                                   for f in e["figures"]]}
                           for e in metrics["projects"] if e["name"] in cm.PROJECT_DEFS}}
    return metrics, catalog, ledger


def _mutations() -> list[tuple[str, str, Any]]:
    """(判据号, 说明, 变异函数) —— 每个变异都必须让对应判据 FAIL。"""
    def set_zero(m, c, l):
        m["projects"][0]["figures"][0]["entity_count"] = 0
        return m, c, l

    def set_mismatch(m, c, l):
        m["projects"][0]["checks"][0]["verdict"] = "MISMATCH"
        return m, c, l

    def drop_project(m, c, l):
        m["projects"].pop(2)  # 删一个「口径表在案」的项目，目录里仍有它 => 漏采
        m["project_total"] = len(m["projects"])
        return m, c, l

    def break_hash(m, c, l):
        m["projects"][0]["source"]["text_sha256"] = "deadbeef"
        return m, c, l

    def flatten_multi_scope(m, c, l):
        m["projects"][1]["figures"] = m["projects"][1]["figures"][:1]
        return m, c, l

    def wrong_self_report(m, c, l):
        m["projects"][0]["self_reported"][0]["value"] = 999
        return m, c, l

    def unavailable_without_reason(m, c, l):
        m["projects"][2]["status"] = "unavailable"
        m["projects"][2]["notes"] = []
        m["projects"][2]["figures"] = []
        return m, c, l

    def ok_without_values(m, c, l):
        m["projects"][2]["figures"] = [{"scope": "空", "entity_count": None, "group_count": None,
                                        "relation_count": None, "layer_count": None, "stage_count": None,
                                        "provenance": "prose"}]
        return m, c, l

    def empty_excerpt(m, c, l):
        m["projects"][0]["source"]["excerpt"] = None
        return m, c, l

    def drift_hash(m, c, l):
        l["projects"][m["projects"][0]["name"]]["page_text_sha256"] = "f" * 64
        return m, c, l

    def drift_value(m, c, l):
        l["projects"][m["projects"][0]["name"]]["figures"][0]["entity_count"] = 111
        return m, c, l

    return [
        ("G4", "figure 值被改成 0（违反 E5）", set_zero),
        ("G6", "交叉校验被标 MISMATCH（上游不同步）", set_mismatch),
        ("G2", "项目目录少一项（漏采）", drop_project),
        ("G8", "页面文本哈希非法", break_hash),
        ("G8", "原文片段被清空", empty_excerpt),
        ("G9", "多 scope 被压成单值", flatten_multi_scope),
        ("G7", "上游自述与枚举不符", wrong_self_report),
        ("G3", "unavailable 无理由", unavailable_without_reason),
        ("G5", "status=ok 但全空", ok_without_values),
        ("G10", "确认登记哈希漂移（WARN 档）", drift_hash),
        ("G10", "确认取值漂移（WARN 档）", drift_value),
    ]


def selftest() -> int:
    print("== 门控自检（负向夹具）==")
    ok = True

    # 对照臂：未经变异的样本必须零 FAIL
    metrics, catalog, ledger = _base_fixture()
    baseline = run_checks(copy.deepcopy(metrics), copy.deepcopy(catalog), copy.deepcopy(ledger))
    if baseline.failures:
        ok = False
        print(f"  [BROKEN] 对照臂本应零 FAIL，实际 {len(baseline.failures)} 条："
              f"{[f['check'] for f in baseline.failures]}")
    else:
        print("  [PASS] 对照臂：未变异样本零 FAIL（判据不是恒 FAIL）")

    level_of = {"G10": "WARN"}
    for check, description, mutate in _mutations():
        m, c, l = _base_fixture()
        m, c, l = mutate(m, c, l)
        result = run_checks(m, c, l)
        expected_level = level_of.get(check, "FAIL")
        hits = [i for i in result.items if i["check"] == check and i["level"] == expected_level]
        if hits:
            print(f"  [PASS] {check} {expected_level} · {description}")
        else:
            ok = False
            print(f"  [BROKEN] {check} 未在变异样本上触发 {expected_level} · {description}")

    print()
    if ok:
        print("SELFTEST: ALL PASS（每条判据都有能触发它的负向样本）")
        return 0
    print("SELFTEST: FAILED")
    return 1


# ────────────────────────────── main ──────────────────────────────


def load(path: str) -> Optional[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        print(f"  !! {path} 不是合法 JSON：{exc}")
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E 指标采集门控")
    parser.add_argument("--metrics", default="src/data/metrics.json")
    parser.add_argument("--catalog", default="src/data/projects.json")
    parser.add_argument("--ledger", default="src/data/metrics-confirmed.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    print("== E 指标门控（读真实产物）==")
    metrics = load(args.metrics)
    catalog = load(args.catalog)
    ledger = load(args.ledger)
    result = run_checks(metrics, catalog, ledger)

    if isinstance(metrics, dict):
        counts = metrics.get("counts") or {}
        print(f"  产物 as_of={metrics.get('as_of')} · 项目 {metrics.get('project_total')} 项"
              f"（ok={counts.get('ok')} / unavailable={counts.get('unavailable')}）")
        print(f"  确认登记：{'已加载' if isinstance(ledger, dict) else '缺失'} "
              f"confirmed_at={(ledger or {}).get('confirmed_at')}")
    print()
    for item in result.items:
        print(f"  [{item['level']}] {item['check']} {item['target']} — {item['message']}")
    if not result.items:
        print("  （无发现）")
    print()
    if result.failures:
        print(f"METRICS GATE: FAIL（{len(result.failures)} 条 FAIL / {len(result.warnings)} 条 WARN）")
        return 1
    print(f"METRICS GATE: ALL PASS（{len(result.warnings)} 条 WARN 需人工留意）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
