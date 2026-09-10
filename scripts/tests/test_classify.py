#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain import classify  # noqa: E402


class ClassifyTypeTest(unittest.TestCase):
    def test_vocab_enums(self):
        self.assertEqual(classify.TYPE_VOCAB[:5], (
            "knowledge-graph", "knowledge-base", "analysis", "tutorial", "methodology"))
        self.assertIn("agent-engineering", classify.DOMAIN_VOCAB)

    def test_known_titles(self):
        cases = {
            "控制理论 ⊗ Agent 设计知识库": "knowledge-base",
            "opencode DAG 依赖分析": "knowledge-graph",
            "LLM 关键节点论文全集（2017–2026）": "knowledge-base",
            "Open Code Review 项目解析知识图谱": "knowledge-graph",
            "GitHub 新手全功能 DAG 教程": "tutorial",
            "算法知识图谱": "knowledge-graph",
            "dsh-manager 插件深度分析：三硬依据依赖分析 + 交互式 DAG": "knowledge-graph",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(classify.classify_type(title), expected)

    def test_type_priority_tutorial_beats_graph(self):
        self.assertEqual(classify.classify_type("GitHub DAG 教程"), "tutorial")

    def test_default_type_is_valid(self):
        self.assertIn(classify.classify_type("random words"), classify.TYPE_VOCAB)

    def test_word_boundary_no_false_positive(self):
        # "reagent" must not match the bare token "agent"
        self.assertNotIn("agent-engineering", classify.classify_domains("reagent chemistry"))

    def test_domains_multi(self):
        domains = classify.classify_domains("控制理论 Agent 设计知识库")
        self.assertEqual(domains, ["agent-engineering", "control-theory"])

    def test_domains_default_valid(self):
        domains = classify.classify_domains("nothing here")
        self.assertTrue(domains)
        self.assertTrue(set(domains) <= set(classify.DOMAIN_VOCAB))

    def test_domains_limited(self):
        text = "agent 控制理论 llm 算法 github 12 factor"
        self.assertLessEqual(len(classify.classify_domains(text, limit=3)), 3)

    def test_normalize_tags_alias(self):
        self.assertEqual(
            classify.normalize_tags(["DAG", "kg", "大模型"]),
            ["knowledge-graph", "llm"],
        )

    def test_normalize_tags_drops_unknown(self):
        self.assertEqual(classify.normalize_tags(["not-a-real-topic"]), [])


if __name__ == "__main__":
    unittest.main()
