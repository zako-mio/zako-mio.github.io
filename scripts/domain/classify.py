#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controlled vocabulary + pure classification functions.

Vocabulary and keyword rules follow the engineering plan (FORM_RULES /
DOMAIN_RULES, P1.6) with alias normalization. Standard library only, no I/O,
fully deterministic so it can be unit-tested offline.
"""
from __future__ import annotations

import re

# --- Controlled vocabulary (must match projects.schema.json enums) ----------
TYPE_VOCAB: tuple[str, ...] = (
    "knowledge-graph",
    "knowledge-base",
    "analysis",
    "tutorial",
    "methodology",
)
DOMAIN_VOCAB: tuple[str, ...] = (
    "agent-engineering",
    "control-theory",
    "llm",
    "algorithms",
    "software-engineering",
    "github",
)

# Deterministic fallbacks: the output contract forbids null/other, and domains
# require >= 1 item, so an unclassifiable repo still gets a valid value.
DEFAULT_TYPE = "analysis"
DEFAULT_DOMAINS: tuple[str, ...] = ("software-engineering",)

# Order matters: the FIRST hit wins (priority top -> bottom, per plan).
TYPE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("tutorial", ("教程", "tutorial", "新手", "入门")),
    (
        "knowledge-graph",
        (
            "知识图谱",
            "knowledge graph",
            "knowledge-graph",
            "dag",
            "依赖链",
            "依赖分析",
            "关系图谱",
            "功能关系图",
            "kg",
        ),
    ),
    (
        "analysis",
        (
            "深度分析",
            "项目解析",
            "解析",
            "analysis",
            "分析报告",
            "源码分析",
            "分析",
        ),
    ),
    (
        "knowledge-base",
        (
            "知识库",
            "knowledge base",
            "knowledge-base",
            "全集",
            "资料库",
            "论文全集",
        ),
    ),
    (
        "methodology",
        ("方法论", "methodology", "12 factor", "12-factor", "原则"),
    ),
)

DOMAIN_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "agent-engineering",
        (
            "agent",
            "agent 设计",
            "llm agent",
            "harness",
            "dsh",
            "opencode",
            "插件",
            "agent-engineering",
        ),
    ),
    ("control-theory", ("控制理论", "control theory", "control-theory")),
    ("llm", ("llm", "大语言模型", "大模型", "论文", "papers")),
    ("algorithms", ("算法", "algorithm", "icpc", "ccpc", "数据结构", "algorithms")),
    (
        "software-engineering",
        (
            "12 factor",
            "12-factor",
            "code review",
            "代码审查",
            "方法论",
            "methodology",
            "software-engineering",
        ),
    ),
    ("github", ("github", "github pages")),
)

# P1.6 alias normalization: arbitrary token/topic -> canonical vocab value.
ALIASES: dict[str, str] = {
    "dag": "knowledge-graph",
    "kg": "knowledge-graph",
    "依赖分析": "knowledge-graph",
    "依赖链": "knowledge-graph",
    "关系图谱": "knowledge-graph",
    "功能关系图": "knowledge-graph",
    "知识图谱": "knowledge-graph",
    "知识库": "knowledge-base",
    "全集": "knowledge-base",
    "资料库": "knowledge-base",
    "大模型": "llm",
    "大语言模型": "llm",
    "论文": "llm",
    "papers": "llm",
    "dsh": "agent-engineering",
    "harness": "agent-engineering",
    "opencode": "agent-engineering",
    "插件": "agent-engineering",
    "控制理论": "control-theory",
    "算法": "algorithms",
    "12 factor": "software-engineering",
    "12-factor": "software-engineering",
    "方法论": "software-engineering",
    "methodology": "software-engineering",
}

_ALL_VOCAB = frozenset(TYPE_VOCAB) | frozenset(DOMAIN_VOCAB)
_ASCII_TOKEN = re.compile(r"^[a-z0-9]+$")


def normalize(text: str | None) -> str:
    """Lower-case and collapse whitespace (deterministic)."""
    return re.sub(r"\s+", " ", (text or "").replace("\u3000", " ")).strip().lower()


def _matches(text: str, keyword: str) -> bool:
    """Substring for CJK/multi-word keys, word-boundary for bare ASCII tokens.

    Word boundaries prevent false positives such as "agent" inside "reagent"
    or "dag" inside "dagre".
    """
    kw = keyword.lower()
    if _ASCII_TOKEN.fullmatch(kw):
        return re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", text) is not None
    return kw in text


def _first_hit(text: str, rules: tuple[tuple[str, tuple[str, ...]], ...]) -> str | None:
    for canonical, keywords in rules:
        if any(_matches(text, kw) for kw in keywords):
            return canonical
    return None


def classify_type(text: str | None) -> str:
    """Single-select type; first rule hit by priority, else DEFAULT_TYPE."""
    hit = _first_hit(normalize(text), TYPE_RULES)
    return hit or DEFAULT_TYPE


def classify_domains(text: str | None, limit: int = 3) -> list[str]:
    """Multi-select domains in vocabulary order, de-duplicated, capped."""
    norm = normalize(text)
    hits = [canon for canon, kws in DOMAIN_RULES if any(_matches(norm, kw) for kw in kws)]
    if not hits:
        return list(DEFAULT_DOMAINS[:limit])
    return hits[:limit]


def normalize_tags(items: list[str] | tuple[str, ...] | None) -> list[str]:
    """Map arbitrary topic strings to canonical vocab values via ALIASES.

    Also passes through canonical vocabulary values unchanged; anything else is
    dropped (controlled vocabulary only).
    """
    out: list[str] = []
    for raw in items or []:
        key = normalize(str(raw))
        canon = ALIASES.get(key, key)
        if canon in _ALL_VOCAB and canon not in out:
            out.append(canon)
    return out


def classify_text(*parts: str | None) -> str:
    """Join non-empty text sources with newlines for stable matching."""
    return "\n".join(p for p in (part or "" for part in parts) if p)
