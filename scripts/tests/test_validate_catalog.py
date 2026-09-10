#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate_catalog  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA = os.path.join(REPO_ROOT, "src", "data", "projects.schema.json")


def valid_payload():
    return {
        "schema_version": "1.0",
        "generated_at": "2026-09-10T00:00:00Z",
        "projects": [
            {
                "name": "demo",
                "title": "Demo",
                "summary": "a summary",
                "type": "analysis",
                "domains": ["llm"],
                "language": "Python",
                "stars": 1,
                "pushed_at": "2026-09-01T00:00:00Z",
                "entry_url": "https://x.github.io/demo/",
                "repo_url": "https://github.com/o/demo",
                "has_pages": True,
                "featured": False,
                "order": 0,
                "section": None,
            }
        ],
    }


class ValidatorTest(unittest.TestCase):
    def setUp(self):
        import json
        with open(SCHEMA, "r", encoding="utf-8") as handle:
            self.schema = json.load(handle)

    def test_valid_payload(self):
        self.assertEqual(validate_catalog.validate(valid_payload(), self.schema), [])

    def test_missing_required_field(self):
        payload = valid_payload()
        del payload["projects"][0]["title"]
        errors = validate_catalog.validate(payload, self.schema)
        paths = [e["path"] for e in errors]
        self.assertIn("$.projects[0].title", paths)

    def test_bad_enum(self):
        payload = valid_payload()
        payload["projects"][0]["type"] = "other"
        paths = [e["path"] for e in validate_catalog.validate(payload, self.schema)]
        self.assertIn("$.projects[0].type", paths)

    def test_additional_property_rejected(self):
        payload = valid_payload()
        payload["projects"][0]["tags"] = ["x"]
        paths = [e["path"] for e in validate_catalog.validate(payload, self.schema)]
        self.assertIn("$.projects[0].tags", paths)

    def test_min_items(self):
        payload = valid_payload()
        payload["projects"] = []
        paths = [e["path"] for e in validate_catalog.validate(payload, self.schema)]
        self.assertIn("$.projects", paths)

    def test_unique_items(self):
        payload = valid_payload()
        payload["projects"][0]["domains"] = ["llm", "llm"]
        paths = [e["path"] for e in validate_catalog.validate(payload, self.schema)]
        self.assertIn("$.projects[0].domains[1]", paths)

    def test_cli_exit_codes(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            good = os.path.join(tmp, "good.json")
            bad = os.path.join(tmp, "bad.json")
            with open(good, "w", encoding="utf-8") as handle:
                json.dump(valid_payload(), handle)
            broken = valid_payload()
            del broken["projects"][0]["entry_url"]
            with open(bad, "w", encoding="utf-8") as handle:
                json.dump(broken, handle)
            script = os.path.join(REPO_ROOT, "scripts", "validate_catalog.py")
            self.assertEqual(subprocess.call([sys.executable, script, good, SCHEMA]), 0)
            self.assertEqual(subprocess.call([sys.executable, script, bad, SCHEMA]), 1)


if __name__ == "__main__":
    unittest.main()
