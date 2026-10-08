#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读行为探针（数值/报告类）：从已构建的 out/ 实产物量化「页间内容重复」。

纪律：
  - 只读，不改任何构建产物（`--out` 只在显式给出时写一份 JSON 读数）；
  - 判据对象 = 真实产物（out/*.html），非源码自述；
  - 文本块以「规范化后的可见文本节点」为单位（去 script/style/noscript）。
  - ⚠ 重合度是**启发式报告项**，⛔ 不判 PASS/FAIL（字面重合对同义改写不敏感）。

用法（本文件为仓库内**常规复验**用副本；原始件留档于 Mission 目录 batch3-rd/probe/）：
    python3 scripts/probes/dup_probe.py [--out <读数.json>]
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_OUT = REPO_ROOT / "out"

PAGES_REL = {
    "首页 /": "index.html",
    "作品 /works": "works/index.html",
    "聚合 /stats": "stats/index.html",
    "关于 /about": "about/index.html",
}

TAG = re.compile(r"<[^>]+>")
DROP = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.S | re.I)


def blocks_of(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = DROP.sub(" ", raw)
    # 以块级标签切段，保留结构边界
    raw = re.sub(r"</(p|li|h1|h2|h3|h4|dt|dd|tr|div|section|article|header|footer|nav|caption)>", "\n", raw)
    raw = TAG.sub(" ", raw)
    text = html.unescape(raw)
    out = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= 4:  # 丢弃导航单字等噪声
            out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_OUT))
    ap.add_argument("--out", default=None, help="可选：把读数 JSON 写到此路径")
    args = ap.parse_args()
    root = Path(args.root)

    pages = {}
    actual = {name: root / rel for name, rel in PAGES_REL.items()}
    for name, path in actual.items():
        if not path.exists():
            print(f"[MISS] {name} -> {path}")
            continue
        pages[name] = blocks_of(path)

    print("== 1) 各页可见文本块数 ==")
    for name, blocks in pages.items():
        uniq = len(set(blocks))
        print(f"  {name:<14} 块 {len(blocks):>4} · 去重 {uniq:>4} · 字符 {sum(len(b) for b in blocks):>6}")

    print("\n== 2) 页间块级重合（A 的独立块中有多少也出现在 B）==")
    names = list(pages)
    print(f"  {'A \\ B':<14}" + "".join(f"{n:>14}" for n in names))
    matrix = {}
    for a in names:
        sa = set(pages[a])
        row = f"  {a:<14}"
        for b in names:
            sb = set(pages[b])
            if a == b:
                row += f"{'--':>14}"
                continue
            inter = len(sa & sb)
            pct = inter / max(len(sa), 1) * 100
            matrix[f"{a}|{b}"] = round(pct, 1)
            row += f"{f'{inter} ({pct:.0f}%)':>14}"
        print(row)

    print("\n== 3) 关键元素跨页出现次数（实产物计数）==")
    probes = {
        "邮箱地址": "1505788754@qq.com",
        "GitHub 主页链接": "github.com/zako-mio",
        "「匿名」字样": "匿名",
        "「技术方向」标签": "技术方向",
        "「最近更新」": "最近更新",
        "作品数量断言 10": ">10<",
    }
    header = f"  {'探针':<18}" + "".join(f"{n:>14}" for n in names)
    print(header)
    counts = {}
    for label, needle in probes.items():
        row = f"  {label:<18}"
        counts[label] = {}
        for n in names:
            raw = actual[n].read_text(encoding="utf-8", errors="replace")
            c = raw.count(needle)
            counts[label][n] = c
            row += f"{c:>14}"
        print(row)

    print("\n== 4) 项目卡/详情链接跨页出现（同一作品被重复列举的程度）==")
    # ⚠ 尾斜杠必选：本项目 `trailingSlash: true` ⇒ 链接写作 `/works/<name>/`；
    #    旧正则（无 `/?`）会恒返回 0（哑火读数）—— 2026-10-08 修正。
    detail_link = re.compile(r'href="/works/([a-z0-9\-]+)/?"')
    links = {}
    for n in names:
        raw = actual[n].read_text(encoding="utf-8", errors="replace")
        seen = detail_link.findall(raw)
        links[n] = len(seen)
        print(f"  {n:<14} 指向具体详情页的链接数 {len(seen):>3} · 去重 {len(set(seen)):>3}")

    result = {
        "blocks": {n: len(v) for n, v in pages.items()},
        "overlap_pct": matrix,
        "element_counts": counts,
        "detail_links": links,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[written] {args.out}")


if __name__ == "__main__":
    main()
