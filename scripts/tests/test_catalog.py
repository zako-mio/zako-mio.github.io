#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain.catalog import build_catalog, sort_projects  # noqa: E402
from domain.models import Project, RepoMetadata  # noqa: E402


class FakeSource:
    def __init__(self, repos, readmes=None):
        self._repos = repos
        self._readmes = readmes or {}
        self.failures = []

    def list_repos(self):
        return list(self._repos)

    def get_readme(self, name):
        return self._readmes.get(name, "")


def meta(name, pages=True, pushed="2026-01-01T00:00:00Z", description="desc"):
    return RepoMetadata(
        name=name,
        html_url=f"https://github.com/o/{name}",
        description=description,
        pushed_at=pushed,
        has_pages=pages,
    )


CONFIG = {
    "schema_version": "1.0",
    "owner": "o",
    "host": "o.github.io",
    "exclude_repos": ["o.github.io"],
    "require_pages": True,
    "max_summary_len": 140,
    "summary_source": "description_first",
}


class BuildCatalogTest(unittest.TestCase):
    def test_filters_pages_and_excludes(self):
        source = FakeSource([
            meta("keep", pages=True),
            meta("no-pages", pages=False),
            meta("o.github.io", pages=True),
        ])
        catalog = build_catalog(source, CONFIG, {"overrides": {}})
        self.assertEqual([p.name for p in catalog.projects], ["keep"])
        self.assertEqual(catalog.stats["skipped"], 2)
        self.assertEqual(catalog.stats["kept"], 1)

    def test_deterministic_sort_pushed_desc(self):
        source = FakeSource([
            meta("old", pushed="2026-01-01T00:00:00Z"),
            meta("new", pushed="2026-03-01T00:00:00Z"),
        ])
        catalog = build_catalog(source, CONFIG, {})
        self.assertEqual([p.name for p in catalog.projects], ["new", "old"])
        # repeated runs identical
        self.assertEqual(
            build_catalog(source, CONFIG, {}).to_dict()["projects"],
            catalog.to_dict()["projects"],
        )

    def test_featured_then_order(self):
        source = FakeSource([
            meta("a", pushed="2026-05-01T00:00:00Z"),
            meta("b", pushed="2026-04-01T00:00:00Z"),
            meta("c", pushed="2026-03-01T00:00:00Z"),
        ])
        overrides = {"overrides": {"c": {"featured": True, "order": 1},
                                   "b": {"order": 0}}}
        catalog = build_catalog(source, CONFIG, overrides)
        self.assertEqual([p.name for p in catalog.projects], ["c", "a", "b"])

    def test_override_merge_fields(self):
        source = FakeSource([meta("a")], {"a": "# Title\n"})
        overrides = {"overrides": {"a": {"alias": "Alias Name", "section": "core"}}}
        project = build_catalog(source, CONFIG, overrides).projects[0]
        self.assertEqual(project.title, "Alias Name")
        self.assertEqual(project.section, "core")

    def test_entry_url_and_summary(self):
        source = FakeSource([meta("a")], {"a": "# A\n"})
        project = build_catalog(source, CONFIG, {}).projects[0]
        self.assertEqual(project.entry_url, "https://o.github.io/a/")
        self.assertEqual(project.summary, "desc")

    def test_classification_wired(self):
        source = FakeSource([meta("gh", description="GitHub 新手 DAG 教程")],
                            {"gh": "# GitHub 新手全功能 DAG 教程\n"})
        project = build_catalog(source, CONFIG, {}).projects[0]
        self.assertEqual(project.type, "tutorial")
        self.assertIn("github", project.domains)

    def test_sort_projects_featured_first(self):
        a = Project("a", "a", "s", "analysis", ["llm"], "u", "u", True, pushed_at="2026-02-01")
        b = Project("b", "b", "s", "analysis", ["llm"], "u", "u", True, pushed_at="2026-03-01")
        b.featured = True
        self.assertEqual([p.name for p in sort_projects([b, a])], ["b", "a"])


if __name__ == "__main__":
    unittest.main()
