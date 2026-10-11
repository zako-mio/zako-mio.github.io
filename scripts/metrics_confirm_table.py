#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E4 人工确认表派生器（2b-2）。

裁决 E4：「产出『提取值 vs 页面原文片段』并列待确认表交用户逐条确认；
登记确认日期 ＋ 当时页面文本哈希。」

★ 本脚本是**纯派生**：全部内容来自 ``src/data/metrics.json``（采集产物），
  ⛔ 不手抄、不重新发明数字（手抄即第二真相源）。
★ 派生件可随时由同一输入复现：同一 metrics.json => 同一张表（逐字节）。

★ W5（批二十）：「更新 → 主页信息级联提醒」的**冻结基线**也挂在本件派生的登记里
  （``--emit-ledger`` 的 ``hub_metadata`` 区，源自 ``src/data/projects.json``）。
  ⛔ 该区**不含任何运行时钟** —— 不得引入第二处 ``as_of``（见
  ``batch18-evidence/W5-pending.md`` §2 约束表）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

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

HUB_METADATA_NOTE = (
    "W5 级联提醒基线（结构化字段快照）。由 scripts/metrics_confirm_table.py 的 "
    "derive_hub_metadata() 纯派生自 src/data/projects.json，⛔ 手工修改无效："
    "scripts/gate_metrics.py 的 C1 会以 src/data/projects.json 重算比对。"
    "⛔ 本区不含任何采集/运行时钟（不引入第二处 as_of）；"
    "⚠ 区内的 pushed_at 是**被监测的上游数据字段**（信号本身），不是运行时钟。"
)


def derive_hub_metadata(catalog: dict[str, Any]) -> dict[str, Any]:
    """从项目目录派生「结构化字段快照」（纯函数，⛔ 不读时钟）。

    取条目**全部**字段（除冗余的 ``name`` —— 它已是本区键，且不可能变化）：
      「仅结构化字段」＝判据作用在**字段**上，⛔ 不因 README/页面这类自由文本的抖动触发
      （自由文本的变化只有**传导到某个字段**才计，例如 README 改动改变了 ``summary``）。
    ⇒ ⛔ 本函数**不开子集白名单**：任何一列的增减/改名都会自动进入快照，
      避免「隐藏子集」把某类变化静默漏掉（计数 == 枚举）。

    ⚠ 键按 name 排序：使同一输入 ⇒ 逐字节同一快照（不受目录排序波动影响）。
    """
    projects: dict[str, Any] = {}
    for item in sorted(catalog.get("projects") or [], key=lambda p: p.get("name") or ""):
        name = item.get("name")
        if not name:
            continue
        projects[name] = {key: value for key, value in item.items() if key != "name"}
    return {"_note": HUB_METADATA_NOTE, "projects": projects}


def diff_hub_metadata(frozen: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    """比对「冻结快照」与「当前目录」的结构化字段（纯函数，⛔ 不读时钟）。

    ★ 本函数是 W5 级联提醒的**唯一比对实现**：派生侧（``--patch-hub-metadata`` 的干跑）
      与门控侧（``gate_metrics`` 的 ``C1``）**共用它** ⇒ 两侧口径不可能漂移。
    ★ 返回逐项差异，顺序确定（先按项目名、再按字段名），kind ∈ {added, removed, changed}。
    """
    items: list[dict[str, Any]] = []
    for name in sorted(set(frozen) | set(current)):
        was, now = frozen.get(name), current.get(name)
        if was is None:
            items.append({"project": name, "field": "*", "old": None, "new": None, "kind": "added"})
            continue
        if now is None:
            items.append({"project": name, "field": "*", "old": None, "new": None, "kind": "removed"})
            continue
        for field in sorted(set(was) | set(now)):
            if was.get(field) != now.get(field):
                items.append({"project": name, "field": field,
                              "old": was.get(field), "new": now.get(field), "kind": "changed"})
    return items


def render_value(value: Any) -> str:
    """差异渲染：字符串原样，其余走紧凑 JSON（⛔ 不用 Python repr，避免与 JSON 形态混淆）。"""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def format_hub_diff(item: dict[str, Any]) -> str:
    """把一条差异渲染成日志行（W5 §4.1 裁决的格式：项目 + 字段 + 旧值→新值）。"""
    if item["kind"] == "added":
        return f"{item['project']}: 新增项目（冻结基线中无此项）"
    if item["kind"] == "removed":
        return f"{item['project']}: 项目已从目录移除（冻结基线仍有此项）"
    return (f"{item['project']}.{item['field']}: "
            f"{render_value(item['old'])} → {render_value(item['new'])}")


def esc(text: Any) -> str:
    """Markdown 表格转义（| 会破坏表格结构）。"""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def _load_catalog(path: str, required: bool) -> Optional[dict[str, Any]]:
    """载入项目目录。⚠ ``required`` 时失败即 rc=1（⛔ 不得静默派生出空快照）。"""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        message = f"项目目录 {path} 不可用：{exc}"
        if required:
            print(json.dumps({"status": "error", "message": message}, ensure_ascii=False), file=sys.stderr)
            return None
        print(f"  !! {message}（本次不涉及 hub_metadata，继续）", file=sys.stderr)
        return {"projects": []}


def _patch_hub_metadata(path: str, catalog: dict[str, Any], write: bool) -> int:
    """只替换登记件的 ``hub_metadata`` 区（⛔ 绝不动 E4 指标确认区）。

    存在理由：W5 基线可**独立于「E4 人工确认」重新冻结** —— 全量 ``--emit-ledger`` 会以
    **当前** ``metrics.json`` 重写确认值，那等于**替用户重新确认**，⛔ 不允许；
    本模式只替换一个区，其余键**逐字节不动**（对象其余部分值相等 ⇒ 序列化后不变）。
    """
    try:
        with open(path, encoding="utf-8") as handle:
            ledger = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": f"{path} 不可用：{exc}"}, ensure_ascii=False),
              file=sys.stderr)
        return 1

    fresh = derive_hub_metadata(catalog)
    old = (ledger.get("hub_metadata") or {}).get("projects") or {}
    changes = diff_hub_metadata(old, fresh["projects"])

    rebuilt: dict[str, Any] = {}
    for key, value in ledger.items():
        if key == "hub_metadata":
            continue  # 稍后在 projects 之后重新插入（保持文件结构稳定）
        rebuilt[key] = value
        if key == "projects":
            rebuilt["hub_metadata"] = fresh
    if "hub_metadata" not in rebuilt:
        rebuilt["hub_metadata"] = fresh

    print("== W5 目录结构化字段快照（级联提醒基线）==")
    print(f"  登记件：{path} · 项目 {len(old)} 项 → {len(fresh['projects'])} 项 · 差异 {len(changes)} 处")
    for item in changes:
        print(f"  [cascade] {format_hub_diff(item)}")
    if not write:
        print("  （干跑：⛔ 未落盘；加 --write 才写）")
        return 0
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rebuilt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"  已落盘 {path}（仅 hub_metadata 区被替换，⛔ E4 指标确认区未动）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从 metrics.json 派生 E4 人工确认表")
    parser.add_argument("--in", dest="src", default="src/data/metrics.json")
    parser.add_argument("--out", dest="out", default="",
                        help="确认表输出路径（用 --patch-hub-metadata 时可省）")
    parser.add_argument("--catalog", default="src/data/projects.json",
                        help="项目目录 —— W5 hub_metadata 快照的派生源")
    parser.add_argument("--confirmed-at", default=None, help="确认日期（确认后回填，形如 2026-10-08）")
    parser.add_argument(
        "--emit-ledger",
        default=None,
        help="同时派生入库的确认登记（src/data/metrics-confirmed.json）—— 冻结锚点，供门控比对",
    )
    parser.add_argument(
        "--patch-hub-metadata",
        dest="patch_hub_metadata",
        default=None,
        help="只更新登记件的 hub_metadata 区（⛔ 不动 E4 指标确认区）；默认干跑，加 --write 落盘",
    )
    parser.add_argument("--write", action="store_true", help="与 --patch-hub-metadata 连用：真正落盘")
    args = parser.parse_args(argv)

    catalog = _load_catalog(args.catalog, required=bool(args.emit_ledger or args.patch_hub_metadata))
    if catalog is None:
        return 1

    if args.patch_hub_metadata:
        return _patch_hub_metadata(args.patch_hub_metadata, catalog, write=args.write)

    if not args.out:
        parser.error("--out 为必填（或用 --patch-hub-metadata 只更新登记件的 W5 基线区）")

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
        ledger_path = _emit_ledger(args, data, catalog)

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


def _emit_ledger(args: argparse.Namespace, data: dict[str, Any], catalog: dict[str, Any]) -> str:
    """派生入库的确认登记（E4 冻结锚点 ＋ W5 级联基线）。

    只承载**机检所需**的四件事，⛔ 不复制散文/报告：
      1. 每项目的页面可见文本 sha256（→ 上游改版后可察觉「确认已过期」）
      2. 每项目每 scope 的**已确认取值**（→ 上游数值变更后可察觉漂移）
      3. 确认日期与口径规范版本（→ 冻结值与判据版本绑定）
      4. ``hub_metadata``：目录条目的结构化字段快照（→ W5「更新 → 主页信息级联提醒」的基线；
         ⛔ 不含运行时钟，见 ``derive_hub_metadata``）
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
        "hub_metadata": derive_hub_metadata(catalog),
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
