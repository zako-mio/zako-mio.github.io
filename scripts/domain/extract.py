#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure extraction functions: title / summary / entry URL.

Rules (REV1 + engineering plan P3):
  * title   : first ATX H1 -> fallback repo.name
  * summary : description first (configurable), README blockquote labelled
              line ('定位/简介') -> first paragraph first sentence, truncated.
  * entry   : has_pages -> ``https://<host>/<repo>/`` else ``repo.html_url``.

Standard library only, no I/O.
"""
from __future__ import annotations

import re
from typing import Optional

from .models import RepoMetadata

_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_H2_RE = re.compile(r"^##\s+")
_ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
_LABEL_RE = re.compile(r"(?:定位|简介|摘要|概述)\s*[:：]\s*(.+)")
_VERSIONISH_RE = re.compile(r"版本|version|更新|升级|创建|v\d", re.IGNORECASE)

# Lines that must not be treated as the leading paragraph of a README.
_NON_PARA_PREFIXES = (">", "|", "```", "[![", "![", "<", "---", "===", "- ", "* ", "+ ")


def norm(text: Optional[str]) -> str:
    """Collapse whitespace and normalise the ideographic space."""
    return re.sub(r"\s+", " ", (text or "").replace("\u3000", " ")).strip()


def strip_md(text: str) -> str:
    """Strip images / links / emphasis markers and leading block markers."""
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    for ch in ("**", "__", "`", "*"):
        s = s.replace(ch, "")
    return norm(re.sub(r"^\s*[>#\-\*\+]+\s*", "", s))


def truncate(text: str, limit: int) -> str:
    """Hard-truncate to ``limit`` characters (summary <= 140 by default)."""
    text = norm(text)
    return text[:limit] if limit and limit > 0 else text


def first_sentence(text: str, limit: int = 140) -> str:
    """First CJK sentence; merge with the second when the first is too short."""
    text = norm(text)
    if not text:
        return ""
    parts = re.split(r"(?<=。)", text)
    if parts and len(parts[0]) >= 15:
        return truncate(parts[0], limit)
    if len(parts) >= 2:
        return truncate(parts[0] + parts[1], limit)
    return truncate(text, limit)


def extract_title(readme: Optional[str], fallback: str) -> str:
    """First ATX H1 (markdown-stripped) or ``fallback`` (usually repo.name)."""
    for line in (readme or "").splitlines():
        m = _H1_RE.match(line)
        if m:
            title = strip_md(m.group(1))
            if title:
                return title
    return norm(fallback)


def _summary_from_readme(readme: str, limit: int) -> str:
    lines = readme.splitlines()
    h1 = next((i for i, line in enumerate(lines) if _H1_RE.match(line)), None)
    if h1 is None:
        return ""

    # Rule 1: blockquote lead-in between H1 and the next H2.
    block: list[str] = []
    started = False
    for line in lines[h1 + 1:]:
        if _H2_RE.match(line):
            break
        if line.lstrip().startswith(">"):
            started = True
            block.append(line)
        elif started:
            break
    if block:
        text = " ".join(strip_md(line) for line in block)
        m = _LABEL_RE.search(text)
        if m:
            return first_sentence(re.split(r"。", m.group(1))[0], limit)
        segments = [seg.strip() for seg in re.split(r"[｜|]", text)]
        candidates = [
            seg
            for seg in segments
            if len(strip_md(seg)) > 15 and not _VERSIONISH_RE.search(seg)
        ]
        if candidates:
            return first_sentence(candidates[0], limit)

    # Rule 2: first natural paragraph after H1 (skip quotes/tables/code/badges).
    para: list[str] = []
    started = False
    for line in lines[h1 + 1:]:
        stripped = line.strip()
        if not started:
            # Skip an explicit 简介/概述/About heading sitting right after H1.
            if re.match(r"^#{2,}\s*(简介|介绍|概述|overview|about)", line, re.IGNORECASE):
                continue
            if not stripped:
                continue
            if stripped.startswith(_NON_PARA_PREFIXES) or _ANY_HEADING_RE.match(stripped):
                continue
            started = True
            para.append(stripped)
            continue
        if not stripped or _H2_RE.match(line) or stripped.startswith(_NON_PARA_PREFIXES):
            break
        para.append(stripped)
    if para:
        return first_sentence(strip_md(para[0]), limit)
    return ""


def extract_summary(
    readme: Optional[str],
    description: Optional[str],
    max_len: int = 140,
    source: str = "description_first",
) -> str:
    """One-line summary.

    ``description_first`` (default, REV1) prefers the repo description and only
    falls back to the README when the description is empty. ``readme_first``
    reverses the priority for callers that prefer long-form prose.
    """
    desc = norm(description)
    readme_text = readme or ""

    def from_description() -> str:
        return truncate(desc, max_len) if desc else ""

    def from_readme() -> str:
        return _summary_from_readme(readme_text, max_len)

    if source == "readme_first":
        return from_readme() or from_description()
    return from_description() or from_readme()


def extract_entry(repo: RepoMetadata, host: str) -> str:
    """Pages root when enabled, otherwise the repository URL."""
    if repo.has_pages:
        return f"https://{host}/{repo.name}/"
    return repo.html_url
