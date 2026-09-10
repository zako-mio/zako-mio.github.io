#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain.models import Catalog, Project, RepoMetadata  # noqa: E402

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src", "data", "projects.schema.json",
)


class ModelsTest(unittest.TestCase):
    def test_repo_metadata_from_api(self):
        meta = RepoMetadata.from_api(
            {
                "name": "demo",
                "full_name": "o/demo",
                "description": "d",
                "html_url": "https://github.com/o/demo",
                "stargazers_count": 3,
                "has_pages": True,
                "topics": ["a"],
                "fork": False,
                "archived": False,
            }
        )
        self.assertEqual(meta.name, "demo")
        self.assertEqual(meta.stars, 3)
        self.assertTrue(meta.has_pages)
        self.assertEqual(meta.topics, ["a"])

    def test_project_to_dict_matches_schema_properties(self):
        project = Project(
            name="demo", title="Demo", summary="s", type="analysis",
            domains=["llm"], entry_url="https://x/", repo_url="https://github.com/o/demo",
            has_pages=False,
        )
        with open(SCHEMA_PATH, "r", encoding="utf-8") as handle:
            schema = json.load(handle)
        allowed = set(schema["properties"]["projects"]["items"]["properties"])
        self.assertEqual(set(project.to_dict()), allowed)

    def test_catalog_to_dict_excludes_stats(self):
        catalog = Catalog(schema_version="1.0", generated_at="2026-01-01T00:00:00Z",
                          projects=[], stats={"kept": 0})
        self.assertEqual(set(catalog.to_dict()), {"schema_version", "generated_at", "projects"})


if __name__ == "__main__":
    unittest.main()
