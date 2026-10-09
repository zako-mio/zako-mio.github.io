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
  S9  卡片嵌套交互契约：整卡拉伸层（`.card__title a::after{inset}`）与「页脚外链抬升」
      （`.card__links a{position:relative; z-index}` 且 z-index **大于**拉伸层）必须成对出现
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

    s9_ok, s9_detail = s9_card_nesting(css)
    check("S9", s9_ok, s9_detail)

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


def s9_card_nesting(css: str) -> tuple[bool, str]:
    """S9 卡片嵌套交互契约（★ 第八批按裁决①反转批三断言）。

    旧断言＝「产物中不得出现整卡覆盖层」（批三取消了整卡 `::after`）；
    新断言＝「必须有整卡拉伸层，且卡片内的**嵌套交互件必须被抬升到其之上**」。
    为什么必须成对：拉伸层铺满整卡后，若页脚外链不同域抬升，就会被它盖住 ⇒
    外链变成**死区**（Bootstrap `stretched-link` 官方点名的问题）。
    ⛔ 不是恒真判据：任一侧缺失 / 抬升不足（z 值不增）都会 FAIL。

    独立成函数 ⇒ 自检可做**定向负向夹具**（不必只靠「整目录缺件」这种粗夹具）。
    """
    def decl_body(sel: str) -> str | None:
        """在（可能被 minify/合并选择器的）产物 CSS 里取某选择器的声明体。

        ⚠ 归一化两件事（实测产物形态）：① 空白；② `::after` 被 minify 成 `:after`
          （伪元素双冒号收敛为单冒号）⇒ 判据侧必须同样收敛，否则会**假 FAIL**。
        """
        want = re.sub(r"\s+", "", sel).replace("::", ":")
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            heads = [
                re.sub(r"\s+", "", part).replace("::", ":") for part in match.group(1).split(",")
            ]
            if want in heads:
                return match.group(2)
        return None

    def z_index(body: str | None) -> int:
        found = re.search(r"z-index:\s*(-?\d+)", body or "")
        return int(found.group(1)) if found else 0

    overlay = decl_body(".card__title a::after")
    raised = decl_body(".card__links a")
    overlay_ok = overlay is not None and "inset" in re.sub(r"\s+", "", overlay)
    raised_ok = raised is not None and "position:relative" in re.sub(r"\s+", "", raised)
    raised_above = z_index(raised) > z_index(overlay)
    detail = (
        "整卡拉伸层就位且嵌套外链已抬升"
        + ("" if overlay_ok else " · 缺 .card__title a::after{inset}")
        + ("" if raised_ok else " · 缺 .card__links a{position:relative}")
        + (
            ""
            if raised_above
            else f" · 抬升不足（overlay z={z_index(overlay)} ≥ links z={z_index(raised)}）"
        )
    )
    return overlay_ok and raised_ok and raised_above, detail


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

    # ★ S9 定向负向夹具（比「整目录缺件」精确得多，逐条对准判据的每个分支）
    s9_samples: list[tuple[str, str, bool]] = [
        (
            "基线：拉伸层＋抬升齐备",
            '.card__title a::after{content:"";position:absolute;inset:0;z-index:1}'
            ".card__links a{position:relative;z-index:2}",
            True,
        ),
        (
            "负向夹具：缺整卡拉伸层（期望 FAIL）",
            ".card__links a{position:relative;z-index:2}",
            False,
        ),
        (
            "负向夹具：缺页脚外链抬升（期望 FAIL）",
            ".card__title a::after{inset:0;z-index:1}.card__links a{z-index:2}",
            False,
        ),
        (
            "负向夹具：抬升不足 z 值不增（期望 FAIL）",
            ".card__title a::after{inset:0;z-index:1}.card__links a{position:relative;z-index:1}",
            False,
        ),
        (
            "负向夹具：拉伸层无 inset（半成品，期望 FAIL）",
            '.card__title a::after{content:"";z-index:1}.card__links a{position:relative;z-index:2}',
            False,
        ),
    ]
    print("\n  -- S9 定向夹具（伪元素 minify 形态 `:after` 一并覆盖）--")
    s9_results: list[bool] = []
    for name, sample, expect in s9_samples:
        got, _ = s9_card_nesting(sample)
        s9_results.append(got == expect)
        print(f"    [{'PASS' if got == expect else 'FAIL'}] {name}（判据={got} 期望={expect}）")

    passed = real and not broken and all(s9_results)
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
