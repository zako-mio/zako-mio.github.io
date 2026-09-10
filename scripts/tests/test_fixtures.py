#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Snapshot-style assertions against real README fixtures."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain import classify, extract  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def read(name):
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as handle:
        return handle.read()


class FixtureSnapshotTest(unittest.TestCase):
    def test_control_theory(self):
        readme = read("control-theory-agent-kb.md")
        title = extract.extract_title(readme, "x")
        self.assertEqual(title, "控制理论 ⊗ Agent 设计知识库")
        self.assertEqual(classify.classify_type(title), "knowledge-base")
        summary = extract.extract_summary(readme, None)
        self.assertTrue(summary.startswith("以 Agent 设计构建为业务核心"))

    def test_github_tutorial(self):
        readme = read("github-dag-tutorial.md")
        title = extract.extract_title(readme, "x")
        self.assertEqual(title, "GitHub 新手全功能 DAG 教程")
        self.assertEqual(classify.classify_type(title), "tutorial")
        self.assertIn("github", classify.classify_domains(title))

    def test_dsh_manager(self):
        readme = read("dsh-manager-analysis.md")
        title = extract.extract_title(readme, "x")
        self.assertEqual(title, "dsh-manager 插件深度分析")
        # title + real description reproduces the pipeline's knowledge-graph label
        blob = classify.classify_text(title, "插件深度分析：E1/E2/E3 三硬依据依赖分析 + 交互式 DAG")
        self.assertEqual(classify.classify_type(blob), "knowledge-graph")
        self.assertIn("agent-engineering", classify.classify_domains(blob))
        summary = extract.extract_summary(readme, None)
        self.assertTrue(summary.startswith("对 "))


if __name__ == "__main__":
    unittest.main()
