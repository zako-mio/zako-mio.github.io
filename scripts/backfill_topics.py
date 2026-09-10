#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XII admin process: backfill repository topics from the controlled vocabulary.

Reads site.config.json, classifies every repo with domain/classify.py and writes
``PUT /repos/{owner}/{repo}/topics`` with ``{"names": [...]}``.

Safety:
  * default is dry-run (prints the plan, performs no writes);
  * writes require the explicit ``--apply`` flag;
  * **additive merge (union)**: existing topics are fetched first and the new
    set is ``existing ∪ desired`` (capped at 20) — topics are never dropped;
  * idempotent: when the union equals the existing set the repo is skipped.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain import classify, extract  # noqa: E402
from sources.github import GitHubSource  # noqa: E402


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def generate_topics(text: str, limit: int = 20) -> list[str]:
    """type + domains, canonical lower-case hyphen tokens, <= limit, ordered."""
    desired: list[str] = []
    for token in (classify.classify_type(text), *classify.classify_domains(text)):
        token = (token or "").strip().lower()
        if token and token not in desired:
            desired.append(token)
    return desired[:limit]


def merge_topics(existing: list[str], desired: list[str], limit: int = 20) -> list[str]:
    """Additive union: keep existing order/policy, append new tokens, never drop."""
    out: list[str] = []
    for token in list(existing or []) + list(desired or []):
        token = (token or "").strip().lower()
        if token and token not in out:
            out.append(token)
    return out[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill GitHub repository topics.")
    parser.add_argument("--config", default="site.config.json", help="path to site.config.json")
    parser.add_argument("--repo", default=None, help="limit to a single repository")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only (default)")
    parser.add_argument("--apply", action="store_true", help="actually PUT topics (opt-in)")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    owner = config.get("owner")
    token = os.environ.get("GH_TOKEN", "")
    if not owner:
        print(json.dumps({"status": "error", "message": "missing owner"}, ensure_ascii=False))
        return 1
    if not token:
        print(json.dumps({"status": "error", "message": "GH_TOKEN required for admin writes"},
                         ensure_ascii=False))
        return 1

    apply = bool(args.apply) and not args.dry_run
    source = GitHubSource(
        owner=owner, api_base=config.get("gh_api_base", "https://api.github.com"), token=token
    )
    exclude = set(config.get("exclude_repos") or [])

    plan: list[dict] = []
    for meta in source.list_repos():
        if meta.name in exclude:
            continue
        if args.repo and meta.name != args.repo:
            continue
        readme = source.get_readme(meta.name)
        title = extract.extract_title(readme, meta.name)
        text = classify.classify_text(title, meta.description, " ".join(meta.topics or []))
        desired = generate_topics(text)
        existing = source.get_repo_topics(meta.name)
        merged = merge_topics(existing, desired)
        changed = sorted(existing) != sorted(merged)
        plan.append(
            {
                "repo": meta.name,
                "desired": desired,
                "existing": existing,
                "merged": merged,
                "changed": changed,
            }
        )

    print(
        json.dumps(
            {
                "mode": "apply" if apply else "dry-run",
                "total": len(plan),
                "planned_changes": sum(1 for item in plan if item["changed"]),
                "plan": plan,
                "failures": list(getattr(source, "failures", []) or []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    if not apply:
        print("dry-run: no topics were written (pass --apply to write).", file=sys.stderr)
        return 0

    for item in plan:
        if item["changed"]:
            source.set_repo_topics(item["repo"], item["merged"])
    print(f"applied topics to {sum(1 for item in plan if item['changed'])} repos.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
