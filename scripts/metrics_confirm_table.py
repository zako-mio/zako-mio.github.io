#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E4 人工确认表派生器（2b-2）。

裁决 E4：「产出『提取值 vs 页面原文片段』并列待确认表交用户逐条确认；
登记确认日期 ＋ 当时页面文本哈希。」

★ 本脚本是**纯派生**：全部内容来自 ``src/data/metrics.json``（采集产物），
  ⛔ 不手抄、不重新发明数字（手抄即第二真相源）。
★ 派生件可随时由同一输入复现：同一 metrics.json => 同一张表（逐字节）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NORMS = (
    ("entity_count", "实体"),
    ("group_count", "组"),
    ("relation_count", "关系"),
    ("layer_count", "拓扑层"),
    ("stage_count", "学习阶段"),
)
SECTION_LABEL = {"dag": "DAG 图谱区", "docs": "文档集群区", "papers": "论文库区"}


def esc(text: Any) -> str:
    """Markdown 表格转义（| 会破坏表格结构）。"""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从 metrics.json 派生 E4 人工确认表")
    parser.add_argument("--in", dest="src", default="src/data/metrics.json")
    parser.add_argument("--out", dest="out", required=True)
    parser.add_argument("--confirmed-at", default=None, help="确认日期（确认后回填，形如 2026-10-08）")
    parser.add_argument(
        "--emit-ledger",
        default=None,
        help="同时派生入库的确认登记（src/data/metrics-confirmed.json）—— 冻结锚点，供门控比对",
    )
    args = parser.parse_args(argv)

    with open(args.src, encoding="utf-8") as handle:
        data = json.load(handle)

    lines: list[str] = []
    lines.append("# E4 人工确认表 · E 指标提取值 vs 页面原文片段")
    lines.append("")
    lines.append("> 任务：`1008-个人主页深化改革` · 第二批 2b-2（硬闸门）")
    lines.append("> 派生自：`src/data/metrics.json`（采集器实跑产物，⛔ 非手抄）")
    lines.append(f"> 采集时点：`{data['as_of']}` ｜ 站点：{data['site']} ｜ 项目数：{data['project_total']}")
    lines.append("> 口径规范：`specs/e-metrics-spec.md` v1.0（E1–E6 已裁）")
    if args.confirmed_at:
        lines.append(f"> ★ 确认状态：**已于 {args.confirmed_at} 由用户逐条确认通过**"
                     "（登记件 `src/data/metrics-confirmed.json`）")
    lines.append("")
    lines.append("## 确认方式")
    lines.append("")
    lines.append("1. 逐行看「提取值」与「页面原文片段」是否一致；")
    lines.append("2. 只对**有异议或无法判断**的行给出反馈（默认视为通过）；")
    lines.append("3. 确认后由主 Agent 回填确认日期并把本表登记为冻结锚点 —— "
                 "之后若上游页面改版，页面文本哈希会变化，可据此察觉「确认已过期」。")
    lines.append("")
    lines.append("## 一、速览（仅有值项）")
    lines.append("")
    lines.append("| 分区 | 项目 | scope | 提取值 | 来源 |")
    lines.append("|---|---|---|---|---|")
    overview = 0
    for entry in data["projects"]:
        section = SECTION_LABEL.get(entry["section"], entry["section"])
        for figure in entry["figures"]:
            pairs = [f"{cn} {figure[norm]}" for norm, cn in NORMS if figure.get(norm) is not None]
            if not pairs:
                continue
            lines.append(
                f"| {esc(section)} | {esc(entry['name'])} | {esc(figure['scope'])} "
                f"| {esc(' · '.join(pairs))} | {esc(figure['provenance'])} |"
            )
            overview += 1
    lines.append("")
    lines.append(f"（{overview} 个 scope 有值；⛔ 未出现的维度＝该 scope 无此项，按 E5 留空，不等于 0）")
    lines.append("")

    lines.append("## 二、逐行明细（提取值 × 页面原文片段）")
    lines.append("")
    lines.append("| 分区 | 项目 | scope | 归一名 | 提取值 | 来源 | 证据（枚举源 / 页面原文片段） |")
    lines.append("|---|---|---|---|---:|---|---|")

    rows = 0
    for entry in data["projects"]:
        section = SECTION_LABEL.get(entry["section"], entry["section"])
        excerpt_by_norm: dict[str, str] = {}
        for hit in entry["prose_hits"]:
            norm = hit.get("normalized")
            if norm and norm not in excerpt_by_norm:
                text = hit.get("excerpt") or f"{hit.get('raw')} {hit.get('label')}"
                excerpt_by_norm[norm] = esc(text)
        multi_scope = len(entry["figures"]) > 1
        for figure in entry["figures"]:
            provenance = str(figure["provenance"])
            for norm, cn in NORMS:
                value = figure.get(norm)
                if provenance.startswith("json"):
                    asset = provenance.split("+")[0].strip()
                    if multi_scope:
                        # ⚠ 散文跨图混排，逐 scope 定位不可靠 => 只给枚举源，⛔ 不张冠李戴
                        evidence = f"枚举源 `{asset}`（散文跨 scope，未逐图定位）"
                    else:
                        prose = excerpt_by_norm.get(norm, "（散文未覆盖该列）")
                        evidence = f"枚举源 `{asset}`；散文：{prose}"
                else:
                    evidence = excerpt_by_norm.get(norm, "（该列无数值，按 E5 留空）")
                shown = "—" if value is None else str(value)
                lines.append(
                    f"| {esc(section)} | {esc(entry['name'])} | {esc(figure['scope'])} | {cn} "
                    f"| {shown} | {esc(provenance)} | {evidence[:220]} |"
                )
                rows += 1
    lines.append("")
    lines.append(f"（共 {rows} 行；`来源` 列 `json:...` = 以 JSON 枚举为权威值，`prose` = 取自页面散文）")
    lines.append("")

    lines.append("## 三、A 级交叉校验结论（JSON 枚举 vs 页面散文）")
    lines.append("")
    lines.append("| 项目 | scope | 归一名 | JSON 枚举 | 散文值 | 结论 |")
    lines.append("|---|---|---|---:|---|---|")
    checks = 0
    for entry in data["projects"]:
        for check in entry.get("checks", []):
            lines.append(
                f"| {esc(entry['name'])} | {esc(check['scope'])} | {check['field']} "
                f"| {check['json_enumerated']} | {check['prose_values']} | {check['verdict']} |"
            )
            checks += 1
    lines.append("")
    lines.append(f"（共 {checks} 项；`match` / `match_partial` = 一致；`ambiguous` = 散文跨 scope 或未覆盖，"
                 "非不一致；`MISMATCH` = 上游不同步，须人工介入）")
    lines.append("")

    lines.append("## 四、抓取失败")
    lines.append("")
    if data.get("failures"):
        for failure in data["failures"]:
            lines.append(f"- `{esc(failure['url'])}` — {esc(failure['reason'])}")
    else:
        lines.append("（本次采集无抓取失败：全部页面与 JSON 资产均 200）")
    lines.append("")

    lines.append("## 五、页面文本哈希（确认锚点）")
    lines.append("")
    lines.append("| 项目 | 页面 URL | 抓取时点 | 可见文本 sha256 |")
    lines.append("|---|---|---|---|")
    for entry in data["projects"]:
        source = entry["source"]
        lines.append(
            f"| {esc(entry['name'])} | {esc(source['url'])} | {esc(source['fetched_at'])} "
            f"| `{esc(source.get('text_sha256') or '—')}` |"
        )
    lines.append("")
    lines.append("> ⚠ 上游页面随时可能改版：本哈希是**确认时点**的指纹；若日后重采哈希变化，"
                 "说明确认已过期，须重新确认（E4 的『防静默失真』机制）。")
    lines.append("")

    lines.append("## 六、未覆盖与非主张")
    lines.append("")
    lines.append(f"- 状态非 ok 的项目：{data.get('unavailable') or '（无）'}")
    lines.append("- `declared_total` / `project_total`："
                 f"{data['declared_total']} / {data['project_total']}"
                 "（二者不等即表示目录里出现了规范未覆盖的项目，按 E5 标 unavailable）")
    lines.append("- ⛔ 本表不主张「上游页面稳定」，也不主张「观感已获确认」；")
    lines.append("- ⛔ 0 值一律不写（E5），故表格中的 `—` 表示「无此项」而非「等于 0」。")
    lines.append("")

    content = "\n".join(lines) + "\n"
    directory = os.path.dirname(os.path.abspath(args.out))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(content)

    ledger_path = None
    if args.emit_ledger:
        ledger_path = _emit_ledger(args, data)

    print(json.dumps(
        {
            "status": "ok",
            "out": args.out,
            "ledger": ledger_path,
            "rows": rows,
            "checks": checks,
            "as_of": data["as_of"],
            "projects": data["project_total"],
            "confirmed_at": args.confirmed_at,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def _emit_ledger(args: argparse.Namespace, data: dict[str, Any]) -> str:
    """派生入库的确认登记（E4 的冻结锚点）。

    只承载**机检所需**的三件事，⛔ 不复制散文/报告：
      1. 每项目的页面可见文本 sha256（→ 上游改版后可察觉「确认已过期」）
      2. 每项目每 scope 的**已确认取值**（→ 上游数值变更后可察觉漂移）
      3. 确认日期与口径规范版本（→ 冻结值与判据版本绑定）
    """
    ledger = {
        "_note": "E4 确认登记（冻结锚点）。由 scripts/metrics_confirm_table.py --emit-ledger 派生，"
                 "⛔ 手工修改无效：门控会以 src/data/metrics.json 重算比对。",
        "ledger_version": "1.0",
        "task": "1008-个人主页深化改革",
        "spec": "specs/e-metrics-spec.md v1.0",
        "decision_ref": "decisions-e-metrics.json#E4",
        "confirmed_at": args.confirmed_at,
        "confirmed_by": "user",
        "as_of": data["as_of"],
        "site": data["site"],
        "declared_total": data["declared_total"],
        "project_total": data["project_total"],
        "projects": {
            entry["name"]: {
                "page_url": entry["source"]["url"],
                "page_text_sha256": entry["source"]["text_sha256"],
                "fetched_at": entry["source"]["fetched_at"],
                "status": entry["status"],
                "figures": [
                    {k: v for k, v in figure.items() if k not in ("provenance",)}
                    for figure in entry["figures"]
                ],
            }
            for entry in data["projects"]
        },
    }
    directory = os.path.dirname(os.path.abspath(args.emit_ledger))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(args.emit_ledger, "w", encoding="utf-8") as handle:
        json.dump(ledger, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return args.emit_ledger


if __name__ == "__main__":
    sys.exit(main())
