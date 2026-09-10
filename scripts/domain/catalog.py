#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use-case layer: build a Catalog from a RepoSource + config + overrides.

Depends only on the domain layer and the ``RepoSource`` port (duck-typed), never
on a concrete adapter. Deterministic: full fetch + stable sort + override merge,
so repeated runs over the same inputs produce the same catalog.
"""
from __future__ import annotations

import datetime
from typing import Any, Optional

from . import classify, extract
from .models import Catalog, Project, RepoMetadata


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _classify_blob(title: str, meta: RepoMetadata) -> str:
    """Title + description + raw topics + alias-normalised topics."""
    canonical = classify.normalize_tags(meta.topics)
    return classify.classify_text(
        title,
        meta.description,
        " ".join(meta.topics or []),
        " ".join(canonical),
    )


def sort_projects(projects: list[Project]) -> list[Project]:
    """featured desc -> order asc -> pushed_at desc (stable, deterministic)."""
    ordered = sorted(projects, key=lambda p: p.pushed_at or "", reverse=True)
    ordered.sort(key=lambda p: (not p.featured, p.order))
    return ordered


def build_catalog(
    source: Any,
    config: dict[str, Any],
    overrides: Optional[dict[str, Any]] = None,
) -> Catalog:
    owner = config.get("owner") or ""
    host = config.get("host") or ""
    exclude = set(config.get("exclude_repos") or [])
    require_pages = bool(config.get("require_pages", True))
    max_len = int(config.get("max_summary_len") or 140)
    schema_version = str(config.get("schema_version") or "1.0")
    summary_source = config.get("summary_source") or "description_first"

    override_map: dict[str, Any] = {}
    if isinstance(overrides, dict) and isinstance(overrides.get("overrides"), dict):
        override_map = overrides["overrides"]
    _ = owner  # reserved for future use; owner is applied by the adapter

    metas: list[RepoMetadata] = list(source.list_repos())
    projects: list[Project] = []
    skipped = 0

    for meta in metas:
        if require_pages and not meta.has_pages:
            skipped += 1
            continue
        if meta.name in exclude:
            skipped += 1
            continue

        readme = source.get_readme(meta.name) or ""
        title = extract.extract_title(readme, meta.name)
        summary = extract.extract_summary(
            readme, meta.description, max_len=max_len, source=summary_source
        )
        blob = _classify_blob(title, meta)
        type_value = classify.classify_type(blob)
        domains = classify.classify_domains(blob)
        entry_url = extract.extract_entry(meta, host)

        override = override_map.get(meta.name) or {}
        if override.get("alias"):
            title = str(override["alias"])

        projects.append(
            Project(
                name=meta.name,
                title=title,
                summary=summary,
                type=type_value,
                domains=domains,
                entry_url=entry_url,
                repo_url=meta.html_url,
                has_pages=bool(meta.has_pages),
                language=meta.language,
                stars=int(meta.stars or 0),
                pushed_at=meta.pushed_at or "",
                featured=bool(override.get("featured", False)),
                order=int(override.get("order", 0) or 0),
                section=override.get("section"),
            )
        )

    projects = sort_projects(projects)
    failures = list(getattr(source, "failures", []) or [])
    return Catalog(
        schema_version=schema_version,
        generated_at=_utc_now(),
        projects=projects,
        stats={
            "fetched": len(metas),
            "kept": len(projects),
            "skipped": skipped,
            "failed": len(failures),
        },
    )
