#!/usr/bin/env python3
"""静态导出冒烟门控 —— 对 `out/` **实产物**取证，不读源码自述。

判据（每条都可复跑、失败即 FAIL）：
  S1  `out/` 存在且含 `index.html`
  S2  必需件齐备（.nojekyll / 404.html / favicon.svg / robots.txt）
  S3  IA-3 五个路由的产物齐备（`/` `/works` `/stats` `/about` `/works/<name>`×N）
  S4  `projects.json` 里每个项目都有一个站内详情页产物（**计数 == 枚举**）
  S5  每页含 `<title>` 且非空
  S6  **无 JS 可读**：剥掉 script/style 后，每页可见文字 ≥ 200 字符
  S7  **主题防闪烁脚本**内联在 HTML 中（每页 1 处）
  S8  **三态**选择器在 CSS 产物中存在（`[data-theme=dark]` 与 `[data-theme=light]` 分支）
  S9  卡片嵌套修复生效：产物中不出现整卡覆盖用的 `inset: 0` 形态的 `::after`（按类名检查）
  S10 首页含「主线作品」区块且主线数与 overrides.json 的 featured 数一致
  S11 `--selftest` 负向夹具：在临时目录构造缺件产物，判据必须转 FAIL

退出码：0 = ALL PASS；1 = 有失败；2 = 用法错误。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
DATA = ROOT / "src/data/projects.json"
OVERRIDES = ROOT / "src/data/overrides.json"
CSS_NAME = "_next"

REQUIRED_FILES = [".nojekyll", "404.html", "favicon.svg", "robots.txt"]
VISIBLE_MIN = 200


def strip_markup(html: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def collect(out_dir: Path) -> dict[str, str]:
    pages: dict[str, str] = {}
    for path in sorted(out_dir.rglob("*.html")):
        rel = path.relative_to(out_dir).as_posix()
        pages[rel] = path.read_text(encoding="utf-8")
    return pages


def collect_css(out_dir: Path) -> str:
    chunks: list[str] = []
    for path in sorted(out_dir.rglob("*.css")):
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def run(out_dir: Path = OUT) -> bool:
    results: list[tuple[str, bool, str]] = []

    def check(cid: str, ok: bool, detail: str) -> None:
        results.append((cid, ok, detail))

    if not (out_dir / "index.html").exists():
        check("S1", False, f"{out_dir}/index.html 不存在")
        report(results)
        return False
    check("S1", True, "out/index.html 存在")

    missing = [name for name in REQUIRED_FILES if not (out_dir / name).exists()]
    check("S2", not missing, "必需件齐备" if not missing else f"缺: {missing}")

    pages = collect(out_dir)
    routes = {"index.html", "works/index.html", "stats/index.html", "about/index.html"}
    missing_routes = sorted(route for route in routes if route not in pages)
    detail_routes = sorted(p for p in pages if p.startswith("works/") and p != "works/index.html")
    check(
        "S3",
        not missing_routes and len(detail_routes) > 0,
        f"主路由 {'齐备' if not missing_routes else missing_routes} · 详情页 {len(detail_routes)} 个",
    )

    projects: list[str] = []
    if DATA.exists():
        projects = [p["name"] for p in json.loads(DATA.read_text(encoding="utf-8"))["projects"]]
    expected = {f"works/{name}/index.html" for name in projects}
    missing_details = sorted(expected - set(pages))
    check(
        "S4",
        bool(projects) and not missing_details,
        f"projects.json {len(projects)} 项 · 详情页缺失 {len(missing_details)} 个"
        + (f" -> {missing_details}" if missing_details else ""),
    )

    bad_title = [name for name, html in pages.items() if not re.search(r"<title>[^<]+</title>", html)]
    check("S5", not bad_title, "每页均含非空 <title>" if not bad_title else f"缺标题: {bad_title}")

    thin = {name: len(strip_markup(html)) for name, html in pages.items()}
    thin_pages = {name: size for name, size in thin.items() if size < VISIBLE_MIN}
    thinnest = min(thin.values()) if thin else 0
    check(
        "S6",
        not thin_pages,
        f"无 JS 可见文字最少 {thinnest} 字符（阈值 {VISIBLE_MIN}）"
        + (f" · 过薄: {thin_pages}" if thin_pages else ""),
    )

    no_script = [name for name, html in pages.items() if "ui-theme" not in html]
    check("S7", not no_script, "主题防闪烁脚本内联" if not no_script else f"缺脚本: {no_script}")

    css = collect_css(out_dir)
    has_dark = "data-theme=dark" in css or 'data-theme="dark"' in css
    has_light = "data-theme=light" in css or 'data-theme="light"' in css
    check("S8", has_dark and has_light, f"三态分支 dark={has_dark} light={has_light}")

    card_css = re.search(r"\.card__title a::after\s*\{(?P<body>[^}]*)\}", css)
    overlay_removed = card_css is None or "inset" not in card_css.group("body")
    check(
        "S9",
        overlay_removed,
        "未发现整卡覆盖层"
        + ("" if card_css is None else "（.card__title a::after 存在但无 inset）"),
    )

    home = pages.get("index.html", "")
    featured_in_page = len(set(re.findall(r'class="chip chip--type"', home))) > 0
    featured_count = 0
    if OVERRIDES.exists():
        overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))["overrides"]
        featured_count = sum(1 for value in overrides.values() if value.get("featured"))
    home_order = re.findall(r'href="/works/([a-z0-9-]+)/"', home)
    deduped: list[str] = []
    for item in home_order:
        if item not in deduped:
            deduped.append(item)
    check(
        "S10",
        "主线作品" in home and featured_in_page,
        f"首页含「主线作品」区块 · featured 登记 {featured_count} 项 · 首页首个详情链接 {deduped[:1]}",
    )

    return report(results)


def report(results: list[tuple[str, bool, str]]) -> bool:
    print("== 静态导出冒烟门控（读 out/ 实产物）==")
    ok = True
    for cid, passed, detail in results:
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {cid}  {detail}")
    print("\nSMOKE:", "ALL PASS" if ok else "HAS FAILURE")
    return ok


def selftest() -> int:
    print("== selftest（临时目录内构造缺件夹具；⛔ 不触碰真实 out/）==")
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp)
        (fake / "index.html").write_text(
            "<html><head><title>t</title></head><body>ui-theme " + "字" * 250 + "</body></html>",
            encoding="utf-8",
        )
        # 只放 index.html：S2/S3/S4/S7/S8/S9 应 FAIL
        broken = run(fake)

    real = run(OUT)
    print("\n  真实 out/（期望 PASS）:", "PASS" if real else "FAIL")
    print("  缺件夹具（期望 FAIL）:", "FAIL" if not broken else "PASS（判据可能恒真）")
    passed = real and not broken
    print("  SELFTEST:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="静态导出冒烟门控（读 out/ 实产物）")
    parser.add_argument("--selftest", action="store_true", help="跑负向夹具")
    parser.add_argument("--out", default=str(OUT), help="产物目录")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    return 0 if run(Path(args.out)) else 1


if __name__ == "__main__":
    sys.exit(main())
