#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Composition root: the only module that knows concrete implementations.

Wires the GitHubSource adapter to the build_catalog use-case, then writes with
failure isolation: ``<out>.tmp`` -> validate (schema + non-empty + minItems) ->
``os.replace()``. A validation failure keeps the previous artifact intact and
exits non-zero. Structured summary goes to stderr for Actions to collect.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.catalog import build_catalog  # noqa: E402
from sources.github import GitHubSource  # noqa: E402
import validate_catalog  # noqa: E402

# env var -> site.config.json key (III Config: deploy values never hard-coded)
ENV_OVERRIDES = {
    "SITE_OWNER": "owner",
    "SITE_HOST": "host",
    "CONTACT_EMAIL": "contact_email",
    "GH_API_BASE": "gh_api_base",
}


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def apply_env_overrides(config: dict[str, Any], env: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if env is None else env
    merged = dict(config)
    for env_key, config_key in ENV_OVERRIDES.items():
        if env.get(env_key):
            merged[config_key] = env[env_key]
    return merged


def _sibling(out_path: str, filename: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(out_path)), filename)


def structural_errors(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Explicit gates beyond the schema: count >= 1 and required fields non-empty."""
    errors: list[dict[str, str]] = []
    projects = payload.get("projects")
    if not isinstance(projects, list) or len(projects) < 1:
        errors.append({"path": "$.projects", "message": "must contain at least one project"})
        return errors
    required = ("name", "title", "summary", "type", "entry_url", "repo_url")
    for index, project in enumerate(projects):
        for key in required:
            if not project.get(key):
                errors.append(
                    {"path": f"$.projects[{index}].{key}", "message": "required field is empty"}
                )
        if not project.get("domains"):
            errors.append(
                {"path": f"$.projects[{index}].domains", "message": "must not be empty"}
            )
    return errors


def write_catalog(out_path: str, payload: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    """Atomic write; returns validation errors (caller decides exit code)."""
    combined = structural_errors(payload) + validate_catalog.validate(payload, schema)
    errors: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for error in combined:
        key = (error.get("path", ""), error.get("message", ""))
        if key not in seen:
            seen.add(key)
            errors.append(error)
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    if errors:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return errors
    os.replace(tmp_path, out_path)
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the tech-hub project catalog.")
    parser.add_argument("--config", default="site.config.json", help="path to site.config.json")
    parser.add_argument("--out", default="src/data/projects.json", help="output catalog path")
    parser.add_argument("--owner", default=None, help="override the GitHub owner")
    args = parser.parse_args(argv)

    config = apply_env_overrides(load_json(args.config))
    if args.owner:
        config["owner"] = args.owner
    if not config.get("owner"):
        print(json.dumps({"status": "error", "message": "missing owner"}, ensure_ascii=False),
              file=sys.stderr)
        return 1

    overrides_path = _sibling(args.out, "overrides.json")
    overrides = load_json(overrides_path) if os.path.exists(overrides_path) else {}
    schema = load_json(_sibling(args.out, "projects.schema.json"))

    source = GitHubSource(
        owner=config["owner"],
        api_base=config.get("gh_api_base", "https://api.github.com"),
        token=os.environ.get("GH_TOKEN", ""),
    )

    try:
        catalog = build_catalog(source, config, overrides)
    except Exception as exc:  # keep previous artifact on any fatal fetch failure
        print(
            json.dumps({"status": "failed", "stage": "fetch", "error": str(exc)},
                       ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        return 1

    errors = write_catalog(args.out, catalog.to_dict(), schema)
    summary = {
        "status": "ok" if not errors else "invalid",
        "out": args.out,
        "generated_at": catalog.generated_at,
        "kept": catalog.stats.get("kept", 0),
        "skipped": catalog.stats.get("skipped", 0),
        "failed": catalog.stats.get("failed", 0),
        "failures": list(getattr(source, "failures", []) or []),
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), file=sys.stderr)

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
