#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E 枢纽聚合 · 指标采集器（2b-1）。

口径唯一真相源：``specs/e-metrics-spec.md`` v1.0（任务 1008-个人主页深化改革）。
本脚本**不发明口径**，只按已裁的 E1–E6 执行：

  E1 不单值化       -> ``figures`` 是数组，每项带 ``scope``；同项目多图并列
  E2 层/阶段分列    -> ``layer_count``（图论分层）与 ``stage_count``（教学分期）各自成列
  E3 分区呈现       -> ``section`` 取 dag / docs / papers，⛔ 不跨区并比
  E4 B 级保真       -> 提取值必须附**页面原文片段**（``source.excerpt``）＋页面文本哈希
  E5 缺失处置       -> 采不到写 ``null`` ＋ ``unavailable`` 理由，⛔ 不写 0
  E6 版本字段       -> 采「项目自称版本」（``version_self``），漂移交由展示层标注

计数纪律（本项目既有教训）：
  - **计数 == 枚举**：A 级一律用 ``len()`` 实算数组，⛔ 不采信 JSON 里 ``meta`` 的自述数字；
    自述数字单独记录在 ``self_reported`` 供比对（枚举 ≠ 自述 ⇒ 上游不同步，是信号不是噪声）。
  - **口径不同不可互校**：只有「同一语义」的字段才做交叉校验。例：散文「9 命令工具」
    （工具种类）与 JSON ``command_index``（72 条命令条目）**不是同一口径**，⛔ 不互校、不混列。

纪律：本机代理可能不可达 ⇒ 显式 ``ProxyHandler({})`` 清空代理（否则走死代理 30s 超时）。

用法::

    python3 scripts/collect_metrics.py                 # 默认 dry-run：只打印摘要，不写盘
    python3 scripts/collect_metrics.py --write          # 落盘 src/data/metrics.json
    python3 scripts/collect_metrics.py --write --only algorithm-knowledge-graph
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# 一、显式口径表（唯一真相源的机读形态；改动此表 = 改口径，须留痕）
# ─────────────────────────────────────────────────────────────────────────────

# 归一名 -> 中文释义（仅用于报告）
NORMALIZED_NAMES = {
    "entity_count": "实体顶点（节点/知识点/插件/包…）",
    "group_count": "实体上层聚合单元（组/分组/知识组）",
    "relation_count": "顶点间有向关系（边/关系边）",
    "layer_count": "图论分层（拓扑层/最长路径分层）",
    "stage_count": "教学分期（学习阶段 basic→advanced）",
}

# E3 分区：项目 -> 分区（分区由规范 §四 裁定，⛔ 不按规模直觉新增）
SECTIONS = {
    "algorithm-knowledge-graph": "dag",
    "deepseek-harness-plugin-dag": "dag",
    "12-factor-methodology-kg": "dag",
    "github-dag-tutorial": "dag",
    "open-code-review-kg": "dag",
    "opencode-dag-analysis": "dag",
    "dsh-manager-analysis": "dag",
    "control-theory-agent-kb": "docs",
    "llm-papers-knowledge-base": "papers",
}

# 可采集性分级（规范 §二；A=有结构化 JSON，B=仅散文数字，C=形态非图谱）
COLLECTABILITY = {
    "algorithm-knowledge-graph": "B",
    "deepseek-harness-plugin-dag": "A",
    "12-factor-methodology-kg": "B",
    "github-dag-tutorial": "B",
    "open-code-review-kg": "A",
    "opencode-dag-analysis": "A",
    "dsh-manager-analysis": "A",
    "control-theory-agent-kb": "B+C",
    "llm-papers-knowledge-base": "B+C",
}

# 每项目的采集定义。
#   json_assets[].counts   : 归一名 -> "$.path"（len() 实算）或 ["$.a","$.b"]（求和）
#   json_assets[].self_reported : 归一名 -> "$.path"（上游 meta 自述，仅供比对）
#   text_labels[]          : 页面散文标签 -> 归一名（用于 B 级提取与 A 级交叉校验）
PROJECT_DEFS: dict[str, dict[str, Any]] = {
    "algorithm-knowledge-graph": {
        "stats_block": True,
        "json_assets": [],
        "text_labels": [
            ("知识点", "entity_count"),
            ("知识组", "group_count"),
            ("关系边", "relation_count"),
            ("学习阶段", "stage_count"),
            ("真实例题", None),  # 规范 §三备注项，非归一名：只留档
        ],
    },
    "deepseek-harness-plugin-dag": {
        "stats_block": True,
        "json_assets": [
            {
                "path": "01-dag-data/webapp-dag.json",
                "scope": "插件级（全量重建 v0.1.7-rc.2）",
                "counts": {
                    "entity_count": "$.nodes",
                    "relation_count": "$.edges",
                    "group_count": "$.groups",
                    "layer_count": "$.layers",
                },
                "self_reported": {
                    "entity_count": "$.meta.plugin_count",
                    "relation_count": "$.meta.edge_count",
                    "group_count": "$.meta.group_count",
                    "layer_count": "$.meta.layer_count",
                },
                "extra": {"seam_edges": "$.seam_edges", "seam_bases": "$.meta.seam_count"},
            }
        ],
        "text_labels": [
            ("插件节点", "entity_count"),
            ("节点间依赖边", "relation_count"),
            ("拓扑层", "layer_count"),
            ("分组", "group_count"),
            ("外部 seam 基座", None),  # 非同口径（基座数 ≠ 实体数），只留档不归列
            ("HTML 插件页", None),
        ],
    },
    "12-factor-methodology-kg": {
        "stats_block": True,
        "json_assets": [],
        "text_labels": [
            ("方法节点", "entity_count"),
            ("分组", "group_count"),
            ("关系边", "relation_count"),
            ("学习阶段", "stage_count"),
        ],
    },
    "github-dag-tutorial": {
        "stats_block": False,  # 数字在副标题，无 stat 区块
        "json_assets": [],
        "text_labels": [
            ("功能节点", "entity_count"),
            ("条关系", "relation_count"),
            ("组", "group_count"),
            ("层", "layer_count"),
        ],
    },
    "open-code-review-kg": {
        "stats_block": True,
        "json_assets": [
            {
                "path": "ai-index.json",
                "scope": "节点索引（v2.0.0）",
                "counts": {"entity_count": "$.node_index", "group_count": "$.group_index"},
                "self_reported": {"entity_count": "$.meta.total_nodes"},
                "extra": {"command_entries": "$.command_index", "assets": "$.asset_index"},
            }
        ],
        "text_labels": [
            ("节点", "entity_count"),
            ("分组", "group_count"),
            ("关系边", "relation_count"),
            # ⚠「命令工具」是工具种类口径，与 JSON command_index（72 条命令条目）不同口径 => 留档不互校
            ("命令工具", None),
            ("使用场景", None),
        ],
    },
    "opencode-dag-analysis": {
        "stats_block": False,  # 数字散在「快速入口」三行
        "json_assets": [
            {
                "path": "01-dag-data/official-dag.json",
                "scope": "图1 官方 DAG",
                "counts": {"entity_count": "$.nodes", "relation_count": "$.edges", "group_count": "$.groups"},
                "extra": {"unit": "$.version_note"},
            },
            {
                "path": "01-dag-data/diff-dag.json",
                "scope": "图2 对比 DAG",
                "counts": {"entity_count": "$.nodes", "relation_count": "$.edges", "group_count": "$.groups"},
            },
            {
                "path": "01-dag-data/modified-dag.json",
                "scope": "图3 改造双层 DAG",
                "counts": {
                    "entity_count": "$.nodes",
                    "relation_count": "$.edges",
                    "group_count": "$.groups",
                    "layer_count": "$.stats.layers",
                },
            },
        ],
        "text_labels": [
            ("包", "entity_count"),
            ("节点", "entity_count"),
            ("边", "relation_count"),
            ("组", "group_count"),
            ("层", "layer_count"),
        ],
    },
    "dsh-manager-analysis": {
        "stats_block": False,
        "json_assets": [
            {
                "path": "02-analysis/dag-data.json",
                "scope": "插件级（术语自成一格）",
                "counts": {
                    "entity_count": ["$.nodes", "$.stubs"],
                    "relation_count": "$.edges_core",
                    "group_count": None,
                },
                "extra": {"features": "$.features", "requirements": "$.requirements", "design_issues": "$.design_issues"},
            }
        ],
        "text_labels": [
            ("边", "relation_count"),
            # ⚠「5 core」只是实体子集（规范 §三 裁 entity = 5 core + 18 stub = 23）=> 不同口径，只留档
            ("core", None),
            ("stub", None),
            ("功能", None),
            ("需求", None),
            ("设计问题", None),
        ],
    },
    "control-theory-agent-kb": {
        "stats_block": False,
        "json_assets": [],
        "text_labels": [
            ("理论知识点", "entity_count"),
            ("核心环", "group_count"),  # 规范 §三已裁：5 核心环 -> group_count
            ("精装房", None),
            ("框架", None),
            ("页", None),
            ("产品画像", None),
        ],
    },
    "llm-papers-knowledge-base": {
        "stats_block": False,
        "json_assets": [],
        "text_labels": [
            ("关键节点", "entity_count"),
            ("技术线", None),
            ("篇", None),
        ],
    },
}

# 已知不在 E 规范 v1.0 项目集内的仓库（规范基于 9 项实探）：
# 不在 PROJECT_DEFS 的项目一律标 unavailable，⛔ 不静默跳过（E5 + 计数==枚举）。
UNKNOWN_REASON = "未纳入 specs/e-metrics-spec.md v1.0 的 9 项目集（规范基于 2026-10-08 实探）"

TAG_RE = re.compile(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", re.S | re.I)
TAG_ANY = re.compile(r"<[^>]+>")
STAT_RE = re.compile(
    r'<div class="stat">\s*<b>(.*?)</b>\s*<span>(.*?)</span>(?:\s*<small>(.*?)</small>)?\s*</div>',
    re.S,
)
QUANT = "个|条|张|篇|门|种|组|层"
VERSION_RE = re.compile(r"\bv\d+(?:\.\d+)+(?:-[\w.]+)?\b")


# ─────────────────────────────────────────────────────────────────────────────
# 二、HTTP（显式清空代理）
# ─────────────────────────────────────────────────────────────────────────────


class Http:
    """无代理 opener；失败返回 (None, reason)，⛔ 不抛穿到调用方。"""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.failures: list[dict[str, str]] = []

    def get(self, url: str) -> tuple[Optional[bytes], Optional[str]]:
        request = urllib.request.Request(url, headers={"User-Agent": "zako-mio-metrics-collector"})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return response.read(), None
        except urllib.error.HTTPError as exc:
            reason = f"http_{exc.code}"
        except urllib.error.URLError as exc:
            reason = f"network_error: {exc.reason}"
        except Exception as exc:  # noqa: BLE001 - 采集器不因单点异常中断
            reason = f"error: {type(exc).__name__}: {exc}"
        self.failures.append({"url": url, "reason": reason})
        return None, reason


# ─────────────────────────────────────────────────────────────────────────────
# 三、解析
# ─────────────────────────────────────────────────────────────────────────────


def visible_text(html: str) -> str:
    text = TAG_RE.sub(" ", html)
    text = TAG_ANY.sub(" ", text)
    for entity, char in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def resolve(obj: Any, path: Optional[str]) -> Any:
    """极简 JSONPath：仅支持 $.a.b（计数用）。"""
    if not path:
        return None
    if path == "$":
        return obj
    if not path.startswith("$."):
        raise ValueError(f"unsupported path: {path}")
    current = obj
    for part in path[2:].split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def count_of(value: Any) -> Optional[int]:
    """计数 == 枚举：对 list/dict 取 len()，⛔ 不读自述数字。"""
    if isinstance(value, (list, dict)):
        return len(value)
    return None


def parse_stats_block(html: str) -> list[dict[str, Any]]:
    """解析「核心统计」区块（实探形态：<h2>核心统计</h2> 之后的 .stat 列表）。"""
    index = html.find("核心统计")
    if index < 0:
        return []
    window = html[index : index + 6000]
    entries = []
    for match in STAT_RE.finditer(window):
        raw, label, small = match.group(1), match.group(2), match.group(3)
        raw, label = visible_text(raw), visible_text(label)
        entries.append(
            {
                "raw": raw,
                "label": label,
                "note": visible_text(small) if small else None,
                "value": int(raw) if raw.isdigit() else None,
            }
        )
    return entries


def find_prose(label: str, text: str) -> list[dict[str, Any]]:
    """在可见文本中定位「数字 + 标签」或「标签 + 数字」，并带出上下文作为证据片段。

    两种语序都要支持：实探发现同一批页面里既有「35 功能节点」（数字在前）
    也有「边 190」（标签在前）——只认前者会静默漏抓（假 MISMATCH 的来源之一）。

    ⚠ 反向模式在中文里**必须**要求右侧是结构性分隔符：中文无空格分词，
    「31 理论知识点 5 核心环」中的 ``5`` 属于「核心环」而非「理论知识点」，
    若只要求右侧为空白就会把 ``5`` 误记到前者名下（实测踩过，导致该项直接降级 unavailable）。
    """
    hits: list[dict[str, Any]] = []
    patterns = (
        re.compile(rf"(\d[\d,]*)\s*(?:{QUANT})?\s*{re.escape(label)}"),
        re.compile(rf"{re.escape(label)}\s+(\d[\d,]*)(?=\s*[·|、，,。；;)）]|\s*$)"),
    )
    for pattern in patterns:
        for match in pattern.finditer(text):
            number = match.group(1).replace(",", "")
            start = max(0, match.start() - 50)
            hits.append(
                {
                    "label": label,
                    "value": int(number) if number.isdigit() else None,
                    "excerpt": text[start : match.end() + 25],
                }
            )
    return hits


# ─────────────────────────────────────────────────────────────────────────────
# 四、采集主流程
# ─────────────────────────────────────────────────────────────────────────────


def collect_project(
    name: str,
    project: dict[str, Any],
    base_url: str,
    http: Http,
) -> dict[str, Any]:
    definition = PROJECT_DEFS.get(name)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    page_url = f"{base_url}/{name}/"
    record: dict[str, Any] = {
        "name": name,
        "title": project.get("title"),
        "section": SECTIONS.get(name, "unclassified"),
        "collectability": COLLECTABILITY.get(name, "unknown"),
        "figures": [],
        "prose_hits": [],
        "self_reported": [],
        "checks": [],
        "extras": {},
        "version_self": None,
        "status": "unavailable",
        "notes": [],
        "source": {"url": page_url, "fetched_at": now, "text_sha256": None, "excerpt": None},
    }
    if definition is None:
        record["notes"].append(UNKNOWN_REASON)
        return record

    html_bytes, reason = http.get(page_url)
    if html_bytes is None:
        record["notes"].append(f"页面抓取失败：{reason}（E5：标 unavailable，⛔ 不写 0）")
        return record
    html = html_bytes.decode("utf-8", "replace")
    text = visible_text(html)
    record["source"]["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()

    versions = VERSION_RE.findall(text)
    if versions:
        record["version_self"] = sorted(set(versions), key=versions.index)[0]

    # --- A 级：JSON 枚举计数（权威值） ---
    for asset in definition.get("json_assets") or []:
        raw, fetch_reason = http.get(f"{page_url}{asset['path']}")
        if raw is None:
            record["notes"].append(f"JSON 资产抓取失败：{asset['path']} — {fetch_reason}")
            continue
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            record["notes"].append(f"JSON 解析失败：{asset['path']} — {exc}")
            continue

        figure: dict[str, Any] = {"scope": asset["scope"], "provenance": f"json:{asset['path']}"}
        for norm, path in (asset.get("counts") or {}).items():
            if path is None:
                figure[norm] = None
                continue
            paths = path if isinstance(path, list) else [path]
            total = 0
            found = False
            for single in paths:
                counted = count_of(resolve(payload, single))
                if counted is not None:
                    total += counted
                    found = True
            # 值 0 且语义为「不适用」（如未分层图）=> 留空，⛔ 不写 0（E5）
            figure[norm] = total if found else None
            if found and total == 0:
                figure[norm] = None
                record["notes"].append(f"{asset['scope']}：{norm} 源值为 0，按 E5 留空（0 ≠ 无）")
        for norm, path in (asset.get("self_reported") or {}).items():
            value = resolve(payload, path)
            if isinstance(value, int):
                record["self_reported"].append(
                    {"scope": asset["scope"], "field": norm, "value": value, "from": f"json:{asset['path']}{path[1:]}"}
                )
        for key, path in (asset.get("extra") or {}).items():
            value = resolve(payload, path)
            if isinstance(value, (list, dict)):
                record["extras"][key] = len(value)
            elif isinstance(value, (str, int)):
                record["extras"][key] = value
        record["figures"].append(figure)

    # --- B 级 / 交叉校验：页面散文（stat 区块优先，其次正文正则） ---
    stats_block = parse_stats_block(html) if definition.get("stats_block") else []
    if stats_block:
        record["source"]["excerpt"] = " ｜ ".join(
            f"{item['raw']} {item['label']}" + (f"（{item['note']}）" if item["note"] else "")
            for item in stats_block
        )
    label_map = {label: norm for label, norm in (definition.get("text_labels") or [])}
    for item in stats_block:
        record["prose_hits"].append(
            {
                "label": item["label"],
                "raw": item["raw"],
                "value": item["value"],
                "normalized": label_map.get(item["label"]),
                "origin": "stats_block",
                "note": item["note"],
            }
        )
    for label, norm in (definition.get("text_labels") or []):
        if any(hit["label"] == label and hit["origin"] == "stats_block" for hit in record["prose_hits"]):
            continue
        for hit in find_prose(label, text):
            record["prose_hits"].append(
                {
                    "label": label,
                    "raw": str(hit["value"]) if hit["value"] is not None else None,
                    "value": hit["value"],
                    "normalized": norm,
                    "origin": "prose",
                    "excerpt": hit["excerpt"],
                }
            )

    if not record["source"]["excerpt"]:
        contexts = [hit["excerpt"] for hit in record["prose_hits"] if hit.get("excerpt")]
        record["source"]["excerpt"] = " ｜ ".join(contexts[:6])[:900] or None

    # --- figures 组装与交叉校验（E1/E5 ＋ 规范 §六「A 级须 JSON 计数 == 散文数字」） ---
    prose_by_norm: dict[str, set[int]] = {}
    zero_labels: set[str] = set()
    for hit in record["prose_hits"]:
        norm = hit.get("normalized")
        value = hit.get("value")
        # E5：0 与「无」语义不同 => 一律不取值，登记后留空（⛔ 不得写 0）
        if norm and value == 0:
            zero_labels.add(hit["label"])
        elif norm and value:
            prose_by_norm.setdefault(norm, set()).add(value)
    if zero_labels:
        record["notes"].append(f"散文值 0（{sorted(zero_labels)}）按 E5 留空 —— 0 ≠ 无")

    if not record["figures"]:
        # B 级：单 scope，全部取自散文数字
        figure = {"scope": "项目页（散文数字）", "provenance": "prose"}
        for norm in NORMALIZED_NAMES:
            values = prose_by_norm.get(norm, set())
            if len(values) == 1:
                figure[norm] = next(iter(values))
            else:
                figure[norm] = None
                if len(values) > 1:
                    record["notes"].append(
                        f"散文对 {norm} 给出多个不同值 {sorted(values)} —— 口径不唯一，"
                        "按 E1/E5 留空待人工确认（E4）"
                    )
        if any(figure.get(norm) is not None for norm in NORMALIZED_NAMES):
            record["figures"].append(figure)
    elif len(record["figures"]) == 1:
        # A 级单 scope：JSON 未覆盖的列由散文补齐（来源显式标注），已有列留给下面的校验
        figure = record["figures"][0]
        filled: list[str] = []
        for norm in NORMALIZED_NAMES:
            if figure.get(norm) is None:
                values = prose_by_norm.get(norm, set())
                figure[norm] = next(iter(values)) if len(values) == 1 else None
                if figure[norm] is not None:
                    filled.append(norm)
        if filled:
            figure["provenance"] = f"{figure['provenance']} + prose({','.join(filled)})"

    # 交叉校验：仅在「JSON 为权威值」的 figure 上做。
    # ⚠ 多 scope 项目（E1 不单值化）的页面散文跨图混排，无法按 scope 局部化 =>
    #    此情形下散文值只能作旁证，⛔ 不判 MISMATCH（否则产出的是「散文没写这一图」的假 FAIL）。
    multi_scope = len(record["figures"]) > 1
    for figure in record["figures"]:
        if not str(figure.get("provenance", "")).startswith("json"):
            continue
        for norm in NORMALIZED_NAMES:
            value = figure.get(norm)
            values = prose_by_norm.get(norm, set())
            if value is None or not values:
                continue
            if values == {value}:
                verdict = "match"
            elif value in values:
                verdict = "match_partial"
            elif multi_scope:
                verdict = "ambiguous"
            else:
                verdict = "MISMATCH"
                record["notes"].append(
                    f"[上游不同步] {figure['scope']} 的 {norm}：JSON 枚举={value}，散文={sorted(values)}"
                )
            record.setdefault("checks", []).append(
                {
                    "scope": figure["scope"],
                    "field": norm,
                    "json_enumerated": value,
                    "prose_values": sorted(values),
                    "verdict": verdict,
                }
            )

    # --- 状态判定 ---
    has_figure = any(
        figure.get(norm) is not None
        for figure in record["figures"]
        for norm in NORMALIZED_NAMES
    )
    if has_figure:
        record["status"] = "ok"
    else:
        record["status"] = "unavailable"
        record["notes"].append("未提取到任何归一名可用的指标值（E5：标 unavailable）")
    return record


def build_report(catalog: dict[str, Any], base_url: str, http: Http) -> dict[str, Any]:
    projects = catalog.get("projects") or []
    entries = [collect_project(item["name"], item, base_url, http) for item in projects]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    unavailable = [entry["name"] for entry in entries if entry["status"] != "ok"]
    return {
        "schema_version": "1.0",
        "spec": "specs/e-metrics-spec.md v1.0（E1–E6 已裁）",
        "as_of": now,
        "site": base_url,
        "project_total": len(projects),
        "declared_total": len(PROJECT_DEFS),
        "counts": {
            "ok": len(entries) - len(unavailable),
            "unavailable": len(unavailable),
            "fetch_failures": len(http.failures),
        },
        "projects": entries,
        "unavailable": unavailable,
        "failures": http.failures,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="采集 E 枢纽聚合指标（默认 dry-run，不写盘）")
    parser.add_argument("--write", action="store_true", help="落盘 src/data/metrics.json")
    parser.add_argument("--out", default="src/data/metrics.json")
    parser.add_argument("--catalog", default="src/data/projects.json")
    parser.add_argument("--config", default="site.config.json")
    parser.add_argument("--only", default=None, help="只采集指定项目（逗号分隔），用于局部重跑")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args(argv)

    if not os.path.exists(args.catalog):
        print(json.dumps({"status": "error", "message": f"缺少目录文件 {args.catalog}，先跑 scripts/cli.py"},
                         ensure_ascii=False), file=sys.stderr)
        return 1

    with open(args.catalog, encoding="utf-8") as handle:
        catalog = json.load(handle)
    with open(args.config, encoding="utf-8") as handle:
        config = json.load(handle)
    host = config.get("host") or "zako-mio.github.io"
    base_url = f"https://{host}"

    if args.only:
        wanted = {name.strip() for name in args.only.split(",") if name.strip()}
        catalog = dict(catalog)
        catalog["projects"] = [item for item in catalog["projects"] if item["name"] in wanted]

    http = Http(timeout=args.timeout)
    report = build_report(catalog, base_url, http)

    summary = {
        "status": "ok",
        "dry_run": not args.write,
        "as_of": report["as_of"],
        "site": report["site"],
        "project_total": report["project_total"],
        "declared_total": report["declared_total"],
        "counts": report["counts"],
        "unavailable": report["unavailable"],
        "fetch_failures": report["failures"],
    }
    if args.write:
        tmp = args.out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, args.out)
        summary["out"] = args.out
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # dry-run 时把明细打到 stderr 便于人工看（E4 的确认表由此衍生）
    if not args.write:
        print("\n--- 逐项目明细（dry-run）---", file=sys.stderr)
        for entry in report["projects"]:
            print(f"[{entry['status']:11}] {entry['name']} ({entry['collectability']} / {entry['section']})", file=sys.stderr)
            for figure in entry["figures"]:
                values = {k: v for k, v in figure.items() if k not in ("scope", "provenance") and v is not None}
                print(f"    scope={figure['scope']} <- {figure['provenance']}  {values}", file=sys.stderr)
            for note in entry["notes"]:
                print(f"    ! {note}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
