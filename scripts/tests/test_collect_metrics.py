#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_metrics 的判据自检（含负向夹具）。

★ 纪律：每个判据都要有「实测会 FAIL」的负向样本，否则无法区分「恒真」与「有效」。
本文件固化了 2026-10-08 实采时踩到的两个真实缺陷（各配一条回归测试）：

  1. 反向语序正则过宽 -> 「31 理论知识点 5 核心环」的 5 被误记到「理论知识点」名下，
     使该项目降级为 unavailable（假命中型缺陷）。
  2. B 级路径漏做 E5 的 0 值处置 -> 散文为 0 时会原样写进 figures（违反「⛔ 不得写 0」）。
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import collect_metrics as cm  # noqa: E402


# ───────────────────────────── 语序解析 ─────────────────────────────


class FindProseTest(unittest.TestCase):
    def test_number_before_label(self):
        hits = cm.find_prose("功能节点", "35 功能节点 / 41 条关系 / 7 组 / 9 层")
        self.assertEqual([h["value"] for h in hits], [35])

    def test_number_before_label_with_quantifier(self):
        hits = cm.find_prose("关键节点", "133 个关键节点")
        self.assertEqual([h["value"] for h in hits], [133])

    def test_label_before_number_after_separator(self):
        hits = cm.find_prose("边", "改造版双层 DAG 节点 129 · 边 190 · 层 8 · 组 43")
        self.assertIn(190, [h["value"] for h in hits])

    def test_regression_chinese_label_must_not_steal_next_number(self):
        """回归 1：中文无空格分词，「理论知识点 5 核心环」的 5 不得算作理论知识点。"""
        hits = cm.find_prose("理论知识点", "31 理论知识点 5 核心环 20 产品画像")
        values = [h["value"] for h in hits]
        self.assertEqual(values, [31])
        self.assertNotIn(5, values)

    def test_regression_group_label_must_not_steal_trailing_number(self):
        """回归 1 的对称面：「核心环 20」的 20 不属于核心环（其正确值是前置的 5）。"""
        hits = cm.find_prose("核心环", "31 控制理论知识点 5 核心环 20 产品画像")
        values = [h["value"] for h in hits]
        self.assertIn(5, values)
        self.assertNotIn(20, values)

    def test_no_hit_returns_empty(self):
        self.assertEqual(cm.find_prose("不存在的标签", "无数字文本"), [])


# ───────────────────────────── 枚举与路径 ─────────────────────────────


class CountEnumTest(unittest.TestCase):
    def test_count_equals_enumeration(self):
        self.assertEqual(cm.count_of([1, 2, 3]), 3)
        self.assertEqual(cm.count_of({"a": 1, "b": 2}), 2)
        self.assertEqual(cm.count_of([]), 0)

    def test_non_container_is_not_counted(self):
        """计数 == 枚举：标量（含上游自述的 meta 数字）不得被当作计数来源。"""
        self.assertIsNone(cm.count_of("239"))
        self.assertIsNone(cm.count_of(239))

    def test_resolve_paths(self):
        payload = {"meta": {"plugin_count": 239}, "nodes": [1, 2]}
        self.assertEqual(cm.resolve(payload, "$.meta.plugin_count"), 239)
        self.assertEqual(len(cm.resolve(payload, "$.nodes")), 2)
        self.assertIsNone(cm.resolve(payload, "$.missing.deep"))

    def test_resolve_rejects_non_dollar_path(self):
        with self.assertRaises(ValueError):
            cm.resolve({}, "meta.x")


# ───────────────────────────── 统计区块解析 ─────────────────────────────


class ParseStatsBlockTest(unittest.TestCase):
    def test_plain_block(self):
        html = '<h2>核心统计</h2><div><div class="stat"><b>372</b><span>知识点</span></div>' \
               '<div class="stat"><b>60</b><span>知识组</span></div></div>'
        entries = cm.parse_stats_block(html)
        self.assertEqual([(e["label"], e["value"]) for e in entries], [("知识点", 372), ("知识组", 60)])

    def test_block_with_small_note(self):
        html = '<h2>核心统计</h2><div class="stats" id="statbar">' \
               '<div class="stat"><b>239</b><span>插件节点</span><small>L1 90 · L2 82 · L3 67</small></div></div>'
        entries = cm.parse_stats_block(html)
        self.assertEqual(entries[0]["value"], 239)
        self.assertEqual(entries[0]["note"], "L1 90 · L2 82 · L3 67")

    def test_non_numeric_value_is_kept_but_not_counted(self):
        html = '<h2>核心统计</h2><div><div class="stat"><b>12+12+10+4</b><span>App+Agent+桥接+工具</span></div></div>'
        entries = cm.parse_stats_block(html)
        self.assertEqual(entries[0]["raw"], "12+12+10+4")
        self.assertIsNone(entries[0]["value"])

    def test_absent_block_returns_empty(self):
        self.assertEqual(cm.parse_stats_block("<h2>其它</h2>"), [])


# ───────────────────────────── 口径表自洽 ─────────────────────────────


class DefinitionTableTest(unittest.TestCase):
    def test_sections_and_defs_cover_same_set(self):
        """计数 == 枚举：分区表与采集定义表的项目集必须逐项相等。"""
        self.assertEqual(set(cm.SECTIONS), set(cm.PROJECT_DEFS))

    def test_normalized_names_are_used_consistently(self):
        """词表里的归一名必须存在于 NORMALIZED_NAMES，防拼写错误静默失效。"""
        for name, definition in cm.PROJECT_DEFS.items():
            for label, norm in definition.get("text_labels") or []:
                self.assertTrue(norm is None or norm in cm.NORMALIZED_NAMES, f"{name}/{label}")
            for asset in definition.get("json_assets") or []:
                for norm in (asset.get("counts") or {}):
                    self.assertIn(norm, cm.NORMALIZED_NAMES, f"{name}/{asset['path']}/{norm}")
                for norm in (asset.get("self_reported") or {}):
                    self.assertIn(norm, cm.NORMALIZED_NAMES, f"{name}/{asset['path']}/{norm}")

    def test_every_definition_declares_collectability(self):
        for name in cm.PROJECT_DEFS:
            self.assertIn(name, cm.COLLECTABILITY)


# ───────────────────────────── 端到端（注入式） ─────────────────────────────


class FakeHttp:
    """按 URL 后缀命中预置响应，用于离线注入式测试。"""

    def __init__(self, pages=None, assets=None, fail=()):
        self.pages = pages or {}
        self.assets = assets or {}
        self.fail = set(fail)
        self.failures = []

    def get(self, url):
        if url in self.fail:
            self.failures.append({"url": url, "reason": "http_404"})
            return None, "http_404"
        for suffix, payload in self.assets.items():
            if url.endswith(suffix):
                return json.dumps(payload).encode("utf-8"), None
        for suffix, html in self.pages.items():
            if url.endswith(suffix):
                return html.encode("utf-8"), None
        self.failures.append({"url": url, "reason": "http_404"})
        return None, "http_404"


BASE = "https://example.test"


def _project(name):
    return {"name": name, "title": name}


class CollectProjectTest(unittest.TestCase):
    def test_e5_zero_prose_value_stays_null(self):
        """负向夹具：散文写 0 时 figure 必须留空（0 ≠ 无）。"""
        html = '<h2>核心统计</h2><div><div class="stat"><b>0</b><span>知识点</span></div>' \
               '<div class="stat"><b>60</b><span>知识组</span></div></div>'
        http = FakeHttp(pages={"algorithm-knowledge-graph/": html})
        record = cm.collect_project("algorithm-knowledge-graph", _project("algorithm-knowledge-graph"), BASE, http)
        figure = record["figures"][0]
        self.assertIsNone(figure["entity_count"])
        self.assertEqual(figure["group_count"], 60)
        self.assertTrue(any("E5" in note for note in record["notes"]))

    def test_mismatch_between_json_enumeration_and_prose_is_flagged(self):
        """负向夹具：JSON 枚举 3 ≠ 散文 9 时必须产出 MISMATCH（上游不同步信号）。"""
        html = '<h2>核心统计</h2><div><div class="stat"><b>9</b><span>插件节点</span></div></div>'
        http = FakeHttp(
            pages={"deepseek-harness-plugin-dag/": html},
            assets={"01-dag-data/webapp-dag.json": {"nodes": [1, 2, 3], "edges": [], "groups": [], "layers": {}}},
        )
        record = cm.collect_project("deepseek-harness-plugin-dag", _project("deepseek-harness-plugin-dag"), BASE, http)
        verdicts = {(c["field"], c["verdict"]) for c in record["checks"]}
        self.assertIn(("entity_count", "MISMATCH"), verdicts)
        self.assertTrue(any("上游不同步" in note for note in record["notes"]))

    def test_matching_json_and_prose_is_not_flagged(self):
        """正例对照臂：与负向夹具同构、仅数值一致 => 不得出现 MISMATCH。"""
        html = '<h2>核心统计</h2><div><div class="stat"><b>3</b><span>插件节点</span></div></div>'
        http = FakeHttp(
            pages={"deepseek-harness-plugin-dag/": html},
            assets={"01-dag-data/webapp-dag.json": {"nodes": [1, 2, 3], "edges": [], "groups": [], "layers": {}}},
        )
        record = cm.collect_project("deepseek-harness-plugin-dag", _project("deepseek-harness-plugin-dag"), BASE, http)
        self.assertNotIn("MISMATCH", {c["verdict"] for c in record["checks"]})

    def test_multi_scope_project_yields_multiple_figures(self):
        """E1：多 scope 项目不得被单值化。"""
        http = FakeHttp(
            pages={"opencode-dag-analysis/": "<h2>快速入口</h2>"},
            assets={
                "official-dag.json": {"nodes": [1] * 36, "edges": [1] * 68, "groups": [1] * 19},
                "diff-dag.json": {"nodes": [1] * 46, "edges": [1] * 68, "groups": [1] * 20},
                "modified-dag.json": {"nodes": [1] * 129, "edges": [1] * 190, "groups": [1] * 43, "stats": {"layers": 8}},
            },
        )
        record = cm.collect_project("opencode-dag-analysis", _project("opencode-dag-analysis"), BASE, http)
        self.assertEqual(len(record["figures"]), 3)
        self.assertEqual([f["entity_count"] for f in record["figures"]], [36, 46, 129])

    def test_project_outside_declared_set_is_unavailable_not_skipped(self):
        """E5：不在规范 9 项集内的项目须显式标 unavailable，⛔ 不静默跳过。"""
        http = FakeHttp(pages={"se-architecture-methodology-kg/": "<html></html>"})
        record = cm.collect_project(
            "se-architecture-methodology-kg", _project("se-architecture-methodology-kg"), BASE, http
        )
        self.assertEqual(record["status"], "unavailable")
        self.assertIn(cm.UNKNOWN_REASON, record["notes"])

    def test_fetch_failure_is_unavailable_with_reason(self):
        name = "algorithm-knowledge-graph"
        http = FakeHttp(fail={f"{BASE}/{name}/"})
        record = cm.collect_project(name, _project(name), BASE, http)
        self.assertEqual(record["status"], "unavailable")
        self.assertTrue(any("页面抓取失败" in note for note in record["notes"]))
        self.assertEqual(http.failures, [{"url": f"{BASE}/{name}/", "reason": "http_404"}])

    def test_source_carries_excerpt_hash_and_time(self):
        """E4：B 级保真要求 —— 提取值必须附原文片段与页面文本哈希。"""
        html = '<h2>核心统计</h2><div><div class="stat"><b>372</b><span>知识点</span></div></div>'
        http = FakeHttp(pages={"algorithm-knowledge-graph/": html})
        record = cm.collect_project("algorithm-knowledge-graph", _project("algorithm-knowledge-graph"), BASE, http)
        self.assertIn("372", record["source"]["excerpt"])
        self.assertEqual(len(record["source"]["text_sha256"]), 64)
        self.assertTrue(record["source"]["fetched_at"].endswith("Z"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
