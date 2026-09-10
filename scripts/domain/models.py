#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Domain entities for the tech-hub catalog.

This module is the innermost layer: it MUST NOT import anything outside the
Python standard library (no network, no framework, no I/O). Entities are plain
dataclasses so they can be constructed, compared and unit-tested offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RepoMetadata:
    """Raw repository metadata as returned by a RepoSource adapter."""

    name: str
    full_name: str = ""
    description: Optional[str] = None
    html_url: str = ""
    homepage: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    pushed_at: Optional[str] = None
    has_pages: bool = False
    topics: list[str] = field(default_factory=list)
    default_branch: Optional[str] = None
    fork: bool = False
    archived: bool = False

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "RepoMetadata":
        """Build an entity from a raw GitHub REST ``/repos`` object."""
        return cls(
            name=raw.get("name") or "",
            full_name=raw.get("full_name") or "",
            description=raw.get("description"),
            html_url=raw.get("html_url") or "",
            homepage=raw.get("homepage"),
            language=raw.get("language"),
            stars=int(raw.get("stargazers_count") or 0),
            pushed_at=raw.get("pushed_at"),
            has_pages=bool(raw.get("has_pages")),
            topics=list(raw.get("topics") or []),
            default_branch=raw.get("default_branch"),
            fork=bool(raw.get("fork")),
            archived=bool(raw.get("archived")),
        )


@dataclass
class Project:
    """A single card in the catalog (stable output contract)."""

    name: str
    title: str
    summary: str
    type: str
    domains: list[str]
    entry_url: str
    repo_url: str
    has_pages: bool
    language: Optional[str] = None
    stars: int = 0
    pushed_at: str = ""
    featured: bool = False
    order: int = 0
    section: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the exact shape allowed by projects.schema.json."""
        return {
            "name": self.name,
            "title": self.title,
            "summary": self.summary,
            "type": self.type,
            "domains": list(self.domains),
            "language": self.language,
            "stars": int(self.stars),
            "pushed_at": self.pushed_at or "",
            "entry_url": self.entry_url,
            "repo_url": self.repo_url,
            "has_pages": bool(self.has_pages),
            "featured": bool(self.featured),
            "order": int(self.order),
            "section": self.section,
        }


@dataclass
class Catalog:
    """The whole generated payload (schema_version + generated_at + projects)."""

    schema_version: str
    generated_at: str
    projects: list[Project] = field(default_factory=list)
    # Runtime-only counters; deliberately excluded from to_dict() (not contract).
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "projects": [p.to_dict() for p in self.projects],
        }
