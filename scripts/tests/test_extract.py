#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain import extract  # noqa: E402
from domain.models import RepoMetadata  # noqa: E402


class ExtractTitleTest(unittest.TestCase):
    def test_first_h1(self):
        self.assertEqual(extract.extract_title("# Hello **World**\n\ntext", "x"), "Hello World")

    def test_fallback_to_repo_name(self):
        self.assertEqual(extract.extract_title("no heading\n", "my-repo"), "my-repo")
        self.assertEqual(extract.extract_title("", "my-repo"), "my-repo")


class ExtractSummaryTest(unittest.TestCase):
    def test_description_priority(self):
        readme = "# T\n\n> **定位**：from readme\n"
        self.assertEqual(
            extract.extract_summary(readme, "from description", max_len=140),
            "from description",
        )

    def test_readme_blockquote_fallback_when_no_description(self):
        readme = (
            "# 控制理论 ⊗ Agent 设计知识库\n\n"
            "> **版本**：v1.2.0\n"
            "> **定位**：以 Agent 设计构建为业务核心，控制理论作为技术工具库引入。\n"
        )
        summary = extract.extract_summary(readme, None, max_len=140)
        self.assertTrue(summary.startswith("以 Agent 设计构建为业务核心"))
        self.assertNotIn("版本", summary)

    def test_readme_first_paragraph_fallback(self):
        readme = "# 标题\n\n这是第一个自然段，用来作为摘要兜底来源，需要足够长。\n"
        self.assertEqual(
            extract.extract_summary(readme, None, max_len=140),
            "这是第一个自然段，用来作为摘要兜底来源，需要足够长。",
        )

    def test_truncate_to_max_len(self):
        long_desc = "啊" * 300
        self.assertEqual(len(extract.extract_summary(None, long_desc, max_len=140)), 140)

    def test_readme_first_mode(self):
        readme = "# T\n\n> **定位**：README wins here.\n"
        self.assertIn(
            "README wins here",
            extract.extract_summary(readme, "desc", max_len=140, source="readme_first"),
        )


class ExtractEntryTest(unittest.TestCase):
    def test_has_pages(self):
        repo = RepoMetadata(name="demo", html_url="https://github.com/o/demo", has_pages=True)
        self.assertEqual(extract.extract_entry(repo, "zako-mio.github.io"),
                         "https://zako-mio.github.io/demo/")

    def test_no_pages_falls_back_to_repo_url(self):
        repo = RepoMetadata(name="demo", html_url="https://github.com/o/demo", has_pages=False)
        self.assertEqual(extract.extract_entry(repo, "zako-mio.github.io"),
                         "https://github.com/o/demo")


if __name__ == "__main__":
    unittest.main()
