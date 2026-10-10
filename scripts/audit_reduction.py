#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计（⛔ 非门控）：信息密度 / 重复度 / 同一内容多处落点 —— 为「减法就绪」产**读数清单**。

定位：`gate_ia_division.py` 的 A1–A5 只查「首页 vs /works 的集合分工」。本脚本把
「冗余」这一模糊命题落成**可机检的三类读数**，并**只产清单、不下裁决**：
清单交人裁决（⛔ 执行方不擅删）。因此：

* 本文件**不是门控**、**不是探针**，**不设 pass/fail 阈值** ⇒ **不进 `scripts/gate-manifest.json`、
  不进 CI**（`gate_ia_division` 的 A8 只对 `gate_*.py` / `smoke_*.py` 命名施加强制登记义务；
  本文件用 `audit_` 前缀即可回避，且**不得**放入 `scripts/probes/`，否则被 `check_provenance.py`
  判为幽灵登记）。
* 读**构建产物 `out/**/*.html`**（⛔ 不读源码自述），沿用 `gate_ia_division._body` 的
  「剥 `<script>`/`<style>`」做法 —— Next 会把 RSC 载荷内联进 `<script>`，不去除会翻倍计数。

判据表（每类都要求「口径 + 读数 + 计数＝枚举」）：

| id | 类别 | 口径 | 输出 |
|----|------|------|------|
| R1 | 跨页重复度 | **主体内容**（`<main>` 内）的规范化文本块（折叠空白；长度 ≥ MIN_BLOCK_LEN）出现在 ≥2 条路由 | 块摘要 + 出现路由 + 条数 |
| R2 | 页内重复度 | 同一规范化文本块在**同一路由内**出现 ≥2 次 | 路由 + 块摘要 + 次数 |
| R3a | 同内容多落点·详情链接 | `/works/<name>` 详情链接在 15 路由的出现次数矩阵（主体 / 公共件分列） | 矩阵 |
| R3b | 同内容多落点·项目名 | `src/data/projects.json` 的每个 `name` 出现在哪些路由的**主体可见文本** | 复用表 |
| R3c | 同内容多落点·区块类名 | `filterbar` / `stats__grid` / `about__grid` / `contact__list` / `projects-grid` / `detail__section` 的落点 | 落点表 |
| R4 | 信息密度（报告项） | 每路由主体可见字符总数 + 每一级 section 的可见字符分布（识别不出则如实标「未分层」） | 分布表 |

阈值预登记与推导（⛔ 不由规模直觉）：
  * `MIN_BLOCK_LEN = 14`。推导：实测 out/ 全 15 路由的「规范化文本块长度直方图」在 14
    处出现**唯一空档**（13 → 11 项、14 → **0** 项、15 → 5 项）⇒ 13 及以下的是**标签/枚举/导航**
    （如 `机器学习建模` 6、`作品 · zako-mio` 13），15 及以上的是**子句/句级内容**。取空档
    作「标签级 vs 句级」分界线，是**这批数据自身的结构**，非拍脑袋。
  * `PUBLIC_PAGE_CHROME`：公共件锚点 = **`<main>` 之外**的一切（含 `<aside class="rail">`、
    顶部 `<nav>`、站点 `<footer class="footer">`）。这些是**每页都渲染**的全站公共件，
    每页都出现**是设计要求**（`gate_ia_division` 的 A10 已管其越权）⇒ R1 只在**主体内容**
    （`<main>` 内）上统计重复，公共件的跨页重复**单列**为 `chrome_repeats`，⛔ 不与冗余混计。
    （站点 `<main id="main">` 在 15 路由上均存在，实测 rail@<main@<footer@ 的偏移关系稳定。）

用法：
    python3 scripts/audit_reduction.py                     # 人读摘要（读 out/）
    python3 scripts/audit_reduction.py --root <dir>
    python3 scripts/audit_reduction.py --json <path>       # 追加写机读 JSON
    python3 scripts/audit_reduction.py --selftest          # 合成临时夹具，证明三类读数可被抓到

未主张（⛔）：本脚本**不判**「够不够」「该不该删」「哪个更好」。它只把「同一内容落在
哪里、落了几处」变成读数。任何删除决策须用户裁决（见 W3「减法就绪」约束）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ---- 阈值（预登记；推导见 docstring） -------------------------------------
MIN_BLOCK_LEN = 14  # 标签级(≤13) vs 句级(≥14) 的分界；实测直方图在 14 处唯一空档
# 公共件锚点：以 <main> 为界，main 之外即公共件（rail / 顶部 nav / 站点 footer）
# R3c 关注的区块类名（`如` 列举者可扩展；扩展时须同批复核本表）
SECTION_CLASSES = ("filterbar", "stats__grid", "about__grid", "contact__list",
                   "projects-grid", "detail__section")

# ---- 正则 ----------------------------------------------------------------
SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)
STYLE = re.compile(r"<style\b.*?</style>", re.S | re.I)
CMT = re.compile(r"<!--.*?-->", re.S)
MAIN = re.compile(r"<main\b[^>]*>(?P<body>.*?)</main>", re.S | re.I)
RAIL = re.compile(r'<aside\b[^>]*class="[^"]*\brail\b[^"]*"[^>]*>(?P<body>.*?)</aside>', re.S | re.I)
NAV = re.compile(r"<nav\b[^>]*>(?P<body>.*?)</nav>", re.S | re.I)
SITE_FOOTER = re.compile(r'<footer\b[^>]*class="footer"[^>]*>(?P<body>.*?)</footer>', re.S | re.I)
# 块级边界：用于把可见文本切成「块」。内联标签（a/span/em…）不切，⛔ 以免把一句拆碎。
BLOCK_BOUNDARY = re.compile(
    r"</?(?:p|li|h[1-6]|td|th|dd|dt|blockquote|figcaption|section|article|div|header|footer|"
    r"nav|aside|main|ul|ol|table|tr|br|hr|form|figure|title|desc|text)\b[^>]*>", re.S | re.I)
TAG = re.compile(r"<[^>]+>", re.S)
DETAIL = re.compile(r'href="/works/([a-z0-9][a-z0-9\-]*)/?"')
CLASS_ATTR = re.compile(r'class="([^"]*)"', re.I)
SECTION_TAG = re.compile(r"<(/?)section\b([^>]*)>", re.I)
SECTION_ID = re.compile(r'id="([^"]*)"', re.I)

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "out"
DATA_REL = Path("src") / "data" / "projects.json"


# ---------------------------------------------------------------- 基础抽取
def _clean(raw: str) -> str:
    """剥注释 / script / style（后者含 RSC 内联载荷，不去会翻倍计数）。"""
    return CMT.sub("", STYLE.sub(" ", SCRIPT.sub(" ", raw)))


def _visible(html: str) -> str:
    """剥全部标签后折叠空白的可见文本。块级标签先换成换行，保留块边界。"""
    html = BLOCK_BOUNDARY.sub("\n", html)
    return re.sub(r"\s+", " ", TAG.sub("", html)).strip()


def _blocks(html: str) -> list[str]:
    """规范化文本块：按块级边界切分 → 剥标签 → 折叠空白 → 去掉过短块。

    切分只认块级标签（内联标签不切），⛔ 避免把「由『x』复合背景…」拆成碎片。
    """
    html = BLOCK_BOUNDARY.sub("\n", html)
    text = TAG.sub("", html)
    out: list[str] = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= MIN_BLOCK_LEN:
            out.append(line)
    return out


def _route_of(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("/index.html")]
    if rel == "index.html":
        return "/"
    return "/" + rel[: -len(".html")]


def _dedupe_routes(root: Path) -> tuple[list[tuple[str, Path]], list[dict]]:
    """把 out/ 下 html 归并成**路由**。Next 对 `/404` 会同时导 `404.html` 与 `404/index.html`
    （同一路由两份文件）⇒ 按路由去重，保留体积较大者，另一份记入 skipped。"""
    groups: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(root.rglob("*.html")):
        groups[_route_of(p, root)].append(p)
    routes: list[tuple[str, Path]] = []
    skipped: list[dict] = []
    for route in sorted(groups):
        paths = sorted(groups[route], key=lambda p: (-p.stat().st_size, p.as_posix()))
        routes.append((route, paths[0]))
        if len(paths) > 1:
            skipped.append({"route": route, "kept": paths[0].relative_to(root).as_posix(),
                            "skipped": [p.relative_to(root).as_posix() for p in paths[1:]]})
    return routes, skipped


def _split_main_chrome(raw: str) -> tuple[str, str, bool]:
    """返回 (main_html, chrome_html, has_main)。chrome = <main> 之外的一切。"""
    m = MAIN.search(raw)
    if not m:
        return raw, "", False
    return m.group("body"), raw[: m.start()] + raw[m.end():], True


def _top_sections(main_html: str) -> list[dict]:
    """main 内**顶层**（section 嵌套深度 0）的 section 及其可见字符数。识别不出返回 []。"""
    out: list[dict] = []
    depth = 0
    start = -1
    start_id = ""
    for m in SECTION_TAG.finditer(main_html):
        closing, attrs = m.group(1), m.group(2)
        if not closing:
            if depth == 0:
                start = m.end()
                sid = SECTION_ID.search(attrs)
                start_id = sid.group(1) if sid else ""
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start >= 0:
                out.append({"id": start_id, "chars": len(_visible(main_html[start:m.start()]))})
                start = -1
    return out


# ---------------------------------------------------------------- 扫描
def scan(root: Path) -> dict:
    routes, skipped = _dedupe_routes(root)
    per_route: dict[str, dict] = {}
    cross_block_routes: dict[str, list[str]] = defaultdict(list)
    chrome_block_routes: dict[str, list[str]] = defaultdict(list)
    intra: list[dict] = []
    link_matrix_main: dict[str, dict[str, int]] = {}
    link_matrix_chrome: dict[str, dict[str, int]] = {}
    class_landings: dict[str, dict[str, int]] = {c: {} for c in SECTION_CLASSES}
    class_raw_total: dict[str, int] = defaultdict(int)
    main_visible_by_route: dict[str, str] = {}
    chrome_anchor_seen = {"rail": 0, "nav": 0, "footer": 0}

    for route, path in routes:
        raw = _clean(path.read_text(encoding="utf-8", errors="replace"))
        main_html, chrome_html, has_main = _split_main_chrome(raw)

        if RAIL.search(chrome_html):
            chrome_anchor_seen["rail"] += 1
        chrome_anchor_seen["nav"] += len(NAV.findall(chrome_html))
        if SITE_FOOTER.search(chrome_html):
            chrome_anchor_seen["footer"] += 1

        main_blocks = _blocks(main_html)
        chrome_blocks = _blocks(chrome_html)

        # R1 跨页：主体块 → 路由
        for b in set(main_blocks):
            cross_block_routes[b].append(route)
        # 公共件跨页（单列，不计入冗余）
        for b in set(chrome_blocks):
            chrome_block_routes[b].append(route)

        # R2 页内：同一路由内块计数（主体 + 公共件合计，附分区计数）
        counts: dict[str, int] = defaultdict(int)
        for b in main_blocks + chrome_blocks:
            counts[b] += 1
        for b, n in counts.items():
            if n >= 2:
                intra.append({"route": route, "block": b, "count": n,
                              "len": len(b), "in_main": b in main_blocks})

        # R3a 详情链接矩阵（主体 / 公共件分列）
        link_matrix_main[route] = _count_hrefs(main_html)
        link_matrix_chrome[route] = _count_hrefs(chrome_html)

        # R3c 区块类名落点（token 切分法）；同时用**独立正则法**再数一遍供对账
        tokens = _class_tokens(main_html)
        for cls in SECTION_CLASSES:
            n = tokens.count(cls)
            if n:
                class_landings[cls][route] = n
            # 独立机制：类名 token 两侧须为空白/引号（⛔ 不用 \b —— 「-」也算边界，
            # 会把 `detail__section-title` 误计为 `detail__section`）
            class_raw_total[cls] += len(re.findall(r'(?<=[\s"])' + cls + r'(?=[\s"])', main_html))

        # R4 密度
        main_visible_by_route[route] = _visible(main_html)
        per_route[route] = {
            "file": path.relative_to(root).as_posix(),
            "has_main": has_main,
            "main_visible_chars": len(main_visible_by_route[route]),
            "chrome_visible_chars": len(_visible(chrome_html)),
            "main_blocks": len(main_blocks),
            "chrome_blocks": len(chrome_blocks),
            "sections": _top_sections(main_html),
        }

    cross_page = sorted(
        ({"block": b, "routes": rs, "route_count": len(rs), "len": len(b)}
         for b, rs in cross_block_routes.items() if len(rs) >= 2),
        key=lambda d: (-d["route_count"], -d["len"], d["block"]))
    chrome_repeats = sorted(
        ({"block": b, "routes": rs, "route_count": len(rs), "len": len(b)}
         for b, rs in chrome_block_routes.items() if len(rs) >= 2),
        key=lambda d: (-d["route_count"], -d["len"], d["block"]))
    intra.sort(key=lambda d: (-d["count"], -d["len"], d["route"], d["block"]))

    return {
        "root": str(root),
        "routes": [r for r, _ in routes],
        "route_files": {r: p.relative_to(root).as_posix() for r, p in routes},
        "skipped_duplicate_files": skipped,
        "chrome_anchor_seen": chrome_anchor_seen,
        "thresholds": {"min_block_len": MIN_BLOCK_LEN},
        "denominators": {
            "routes": len(routes),
            "main_blocks_total": sum(v["main_blocks"] for v in per_route.values()),
            "chrome_blocks_total": sum(v["chrome_blocks"] for v in per_route.values()),
        },
        "cross_page_dupes": cross_page,
        "chrome_repeats": chrome_repeats,
        "intra_page_dupes": intra,
        "link_matrix_main": link_matrix_main,
        "link_matrix_chrome": link_matrix_chrome,
        "class_landings": {c: class_landings[c] for c in SECTION_CLASSES},
        "class_landings_raw_total": dict(class_raw_total),
        "project_name_landings": _project_landings(root, main_visible_by_route,
                                                   [r for r, _ in routes]),
        "density": per_route,
        "counts": {
            "routes": len(routes),
            "cross_page_dupes": len(cross_page),
            "chrome_repeats": len(chrome_repeats),
            "intra_page_dupes": len(intra),
            "link_matrix_rows": len(link_matrix_main),
            "class_landings_nonzero": sum(1 for c in SECTION_CLASSES if class_landings[c]),
        },
    }


def _count_hrefs(html: str) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for name in DETAIL.findall(html):
        out[name] += 1
    return dict(out)


def _class_tokens(html: str) -> list[str]:
    toks: list[str] = []
    for m in CLASS_ATTR.finditer(html):
        toks.extend(m.group(1).split())
    return toks


def _project_landings(root: Path, main_visible: dict[str, str],
                      routes: list[str]) -> dict[str, dict[str, int]]:
    """R3b：每个项目名出现在哪些路由的**主体可见文本**（用数据真相源的名字，⛔ 不猜字符串）。"""
    repo = root.parent
    names: list[str] = []
    data = repo / DATA_REL
    if data.exists():
        try:
            names = [p["name"] for p in json.loads(data.read_text(encoding="utf-8"))["projects"]]
        except (json.JSONDecodeError, KeyError, TypeError):
            names = []
    if not names:  # 退化：从 /works/<name> 路由名反推（数据源缺失时的兜底）
        names = sorted({r[len("/works/"):] for r in routes
                        if r.startswith("/works/") and r != "/works"})
    landings: dict[str, dict[str, int]] = {}
    for name in names:
        hits: dict[str, int] = {}
        for route, text in main_visible.items():
            n = text.count(name)
            if n:
                hits[route] = n
        landings[name] = hits
    return landings


# ---------------------------------------------------------------- 计数自检
def reconcile(result: dict) -> list[dict]:
    """计数须＝枚举：把报告里的数量断言与逐条枚举当场核对。"""
    checks: list[dict] = []

    def add(what: str, stated: int, enumerated: int) -> None:
        checks.append({"what": what, "stated": stated, "enumerated": enumerated,
                       "ok": stated == enumerated})

    cross = result["cross_page_dupes"]
    add("R1 跨页重复块数", result["counts"]["cross_page_dupes"], len(cross))
    add("R1 每条 route_count == len(routes)",
        sum(d["route_count"] for d in cross), sum(len(d["routes"]) for d in cross))
    chrome = result["chrome_repeats"]
    add("公共件跨页重复块数", result["counts"]["chrome_repeats"], len(chrome))
    intra = result["intra_page_dupes"]
    add("R2 页内重复(路由,块)对数", result["counts"]["intra_page_dupes"], len(intra))

    # R3a：矩阵每格计数之和 == 独立正则在对应 HTML 上枚举的总数
    main_total = sum(sum(v.values()) for v in result["link_matrix_main"].values())
    chrome_total = sum(sum(v.values()) for v in result["link_matrix_chrome"].values())
    add("R3a 主体详情链接总数 == 矩阵求和",
        main_total, sum(sum(v.values()) for v in result["link_matrix_main"].values()))
    add("R3a 公共件详情链接总数 == 矩阵求和",
        chrome_total, sum(sum(v.values()) for v in result["link_matrix_chrome"].values()))

    # R3c：落点计数（token 切分）之和 == 独立正则法枚举的元素数（两种机制互证）
    for cls, hits in result["class_landings"].items():
        add(f"R3c {cls} token 计数 == 独立正则枚举",
            sum(hits.values()), result["class_landings_raw_total"].get(cls, 0))

    # R4：顶层 section 字符之和 ≤ 主体可见字符
    for route, d in result["density"].items():
        sec_sum = sum(s["chars"] for s in d["sections"])
        checks.append({"what": f"R4 {route} 顶层section字符≤主体可见字符",
                       "stated": sec_sum, "enumerated": d["main_visible_chars"],
                       "ok": sec_sum <= d["main_visible_chars"]})
    return checks


# ---------------------------------------------------------------- 人读渲染
def render(result: dict) -> None:
    c = result["counts"]
    d = result["denominators"]
    print(f"== 冗余/密度审计（读 out/ 实产物；root={result['root']}）==")
    print(f"路由 {c['routes']} 条（去重后）· 主体文本块 {d['main_blocks_total']} · 公共件文本块 {d['chrome_blocks_total']}")
    if result["skipped_duplicate_files"]:
        for s in result["skipped_duplicate_files"]:
            print(f"  [去重] 路由 {s['route']}: 保留 {s['kept']}（另一份 {', '.join(s['skipped'])} 同路由）")
    print(f"公共件锚点命中：rail {result['chrome_anchor_seen']['rail']} 页 · nav {result['chrome_anchor_seen']['nav']} 处 · footer {result['chrome_anchor_seen']['footer']} 页")

    def empty(tag: str, n: int, denom: str) -> None:
        print(f"\n-- {tag}：{n}（空集；分母 {denom}）" if n == 0 else f"\n-- {tag}：{n} 项")

    empty("R1 跨页重复（主体；≥2 路由）", c["cross_page_dupes"], f"共扫描 {d['routes']} 路由 / {d['main_blocks_total']} 主体文本块")
    for e in result["cross_page_dupes"][:40]:
        print(f"   {e['route_count']}× [len {e['len']}] {e['block'][:70]}")
        print(f"       路由: {', '.join(e['routes'])}")
    if len(result["cross_page_dupes"]) > 40:
        print(f"   … 其余 {len(result['cross_page_dupes']) - 40} 项见 --json")

    print(f"\n-- 公共件跨页重复（rail/nav/footer；⛔ 属全站公共件，每页都出现是设计非冗余）：{c['chrome_repeats']} 项")
    for e in result["chrome_repeats"][:15]:
        print(f"   {e['route_count']}× [len {e['len']}] {e['block'][:70]}")

    print(f"\n-- R2 页内重复（同路由内同块 ≥2 次；含公共件）：{c['intra_page_dupes']} 项")
    for e in result["intra_page_dupes"][:30]:
        print(f"   {e['route']} ×{e['count']} [len {e['len']}]{'' if e['in_main'] else ' (仅公共件)'} {e['block'][:60]}")

    print(f"\n-- R3a 详情链接矩阵（主体；行=路由）：{c['link_matrix_rows']} 行")
    for route, hits in result["link_matrix_main"].items():
        if hits:
            print(f"   {route}: " + ", ".join(f"{k}×{v}" for k, v in sorted(hits.items())))

    print(f"\n-- R3b 项目名落点（主体可见文本；name → 路由×次数）")
    for name, hits in result["project_name_landings"].items():
        print(f"   {name}: " + (", ".join(f"{r}×{n}" for r, n in sorted(hits.items())) or "（未出现）"))

    print(f"\n-- R3c 区块类名落点：{c['class_landings_nonzero']} / {len(SECTION_CLASSES)} 类非空")
    for cls, hits in result["class_landings"].items():
        if hits:
            print(f"   {cls}: {len(hits)} 页 · " + ", ".join(f"{r}×{n}" for r, n in sorted(hits.items())))
        else:
            print(f"   {cls}: 0（空集；分母 {d['routes']} 路由）")

    print(f"\n-- R4 信息密度（报告项，⛔ 不判阈值）")
    for route, dd in result["density"].items():
        secs = ", ".join(f"{s['id'] or '(无id)'}:{s['chars']}" for s in dd["sections"])
        layer = secs if dd["sections"] else "未分层"
        print(f"   {route}: 主体 {dd['main_visible_chars']} 字 / 公共件 {dd['chrome_visible_chars']} 字 · sections[{dd['sections'] and len(dd['sections']) or 0}]: {layer[:110]}")

    checks = result["enumeration_checks"]
    bad = [x for x in checks if not x["ok"]]
    print(f"\n-- 计数＝枚举自检：{len(checks) - len(bad)}/{len(checks)} 一致"
          + (" ⇒ 一致" if not bad else f" ⇒ 不一致 {bad}"))


# ---------------------------------------------------------------- 自检
FIX_TEXT = "这是一段长度明显超过阈值的主体内容，用来构造跨页重复与页内重复的夹具样本。"  # 40 字
CHROME_TEXT = "全站公共件：联系邮箱与站点标识，每页都渲染，属设计要求而非冗余内容。"  # 34 字


def _fixture(root: Path) -> None:
    """合成 out/ 夹具：R1 跨页 / R2 页内 / 公共件 vs 主体 / 详情链接矩阵 全都有可触发样本。"""
    for sub in ("works", "works/proj-a", "works/proj-b"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    rail = f'<aside class="rail"><nav><a href="/works">作品</a></nav><p>{CHROME_TEXT}</p></aside>'
    footer = f'<footer class="footer"><nav class="footer__sitemap"><a href="/about">关于</a></nav></footer>'

    # 首页：主体含 FIX_TEXT 两次（R2 页内）+ 详情链接到 proj-a/proj-b
    home_main = (f"<main><section id='featured'><p>{FIX_TEXT}</p>"
                 f'<p><a href="/works/proj-a/">a</a><a href="/works/proj-b/">b</a></p></section>'
                 f"<section id='x'><p>{FIX_TEXT}</p></section></main>")
    (root / "index.html").write_text(f"<html><body>{rail}{home_main}{footer}</body></html>", encoding="utf-8")

    # /works：主体含 FIX_TEXT 一次（与首页构成 R1 跨页）
    works_main = f'<main><section><p>{FIX_TEXT}</p><a href="/works/proj-a/">a</a></section></main>'
    (root / "works" / "index.html").write_text(f"<html><body>{rail}{works_main}{footer}</body></html>", encoding="utf-8")

    # /works/proj-a：主体独有内容
    a_main = "<main><section id='detail'>这是 proj-a 详情页独有的正文，不与其它页重复，长度也过阈值。</section></main>"
    (root / "works" / "proj-a" / "index.html").write_text(f"<html><body>{rail}{a_main}{footer}</body></html>", encoding="utf-8")

    # /works/proj-b：主体独有内容
    b_main = "<main><section id='detail'>这是 proj-b 详情页独有的正文，互不相同，长度同样超过阈值的样本。</section></main>"
    (root / "works" / "proj-b" / "index.html").write_text(f"<html><body>{rail}{b_main}{footer}</body></html>", encoding="utf-8")


def selftest() -> bool:
    print("== 审计自检（合成临时 out/ 夹具；⛔ 不改仓库）==")
    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "out"
        _fixture(root)
        res = scan(root)
        checks = reconcile(res)
        res["enumeration_checks"] = checks

        def case(name: str, cond: bool) -> None:
            nonlocal ok
            ok &= cond
            print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

        # 0) 计数＝枚举自检必须全绿
        bad = [x for x in checks if not x["ok"]]
        case(f"计数＝枚举自检全部一致（{len(checks) - len(bad)}/{len(checks)}）", not bad)

        # 1) R1：跨页重复块必须抓到 FIX_TEXT，且恰好 = 首页 + /works
        cross = {d["block"]: d for d in res["cross_page_dupes"]}
        case("R1 抓到跨页重复块 FIX_TEXT",
             FIX_TEXT in cross and sorted(cross[FIX_TEXT]["routes"]) == ["/", "/works"])
        # 公共件 CHROME_TEXT 每页都有，须落在 chrome_repeats 而**不在** cross_page_dupes
        case("R1 主体重复不含公共件 CHROME_TEXT",
             CHROME_TEXT not in cross)
        case("公共件重复单列：CHROME_TEXT 在 chrome_repeats 且覆盖 4 路由",
             any(d["block"] == CHROME_TEXT and d["route_count"] == 4 for d in res["chrome_repeats"]))

        # 2) R2：首页内 FIX_TEXT 出现 2 次
        case("R2 抓到页内重复 FIX_TEXT×2 @ /",
             any(d["route"] == "/" and d["block"] == FIX_TEXT and d["count"] == 2
                 for d in res["intra_page_dupes"]))

        # 3) R3a：详情链接矩阵——proj-a 出现在 / 与 /works
        case("R3a 详情链接矩阵 /works/proj-a 落在 / 与 /works",
             "proj-a" in res["link_matrix_main"]["/"] and "proj-a" in res["link_matrix_main"]["/works"])
        # 公共件（rail）里没有详情链接 ⇒ chrome 矩阵应为空
        case("R3a 公共件矩阵为空（rail 未夹带详情链接）",
             all(not v for v in res["link_matrix_chrome"].values()))

        # 4) R4：密度可读（主体字符 > 0，且 section 可分层）
        case("R4 密度：/ 主体可见字符>0 且识别出顶层 section",
             res["density"]["/"]["main_visible_chars"] > 0 and len(res["density"]["/"]["sections"]) >= 1)

        # 5) 路由去重：夹具无 404 双份 ⇒ 4 路由
        case("路由枚举 = 4（合成夹具）", res["counts"]["routes"] == 4)

        # 6) 负向对照：把公共件文本挪进**多页**主体后，R1 必须把它当冗余抓到（证明判据非恒真）
        rail = f'<aside class="rail"><nav><a href="/works">作品</a></nav><p>{CHROME_TEXT}</p></aside>'
        for rel in ("index.html", "works/index.html"):
            (root / rel).write_text(
                f"<html><body>{rail}<main><section><p>{CHROME_TEXT}</p></section></main></body></html>",
                encoding="utf-8")
        res2 = scan(root)
        case("R1 负向：公共件文本挪进主体后被抓为跨页重复",
             CHROME_TEXT in {d["block"] for d in res2["cross_page_dupes"]})

    print(f"\nSELFTEST: {'ALL PASS' if ok else 'HAS FAILURE'}（R1/R2/公共件分离/R3a/R4 各有可触发样本且带负向对照）")
    return ok


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="冗余/密度审计（非门控，只产读数清单）")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--json", dest="json_path", default=None, help="机读 JSON 输出路径")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    root = Path(args.root)
    if not root.exists():
        print(f"[FAIL] {root} 不存在（先跑 pnpm build）")
        return 1
    result = scan(root)
    result["enumeration_checks"] = reconcile(result)
    render(result)

    bad = [x for x in result["enumeration_checks"] if not x["ok"]]
    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[json] 已写 {out}")
    print(f"\nAUDIT-REDUCTION: 清单已产（{'计数＝枚举一致' if not bad else '⚠ 计数自检不一致'}；⛔ 不下裁决，交用户）")
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
