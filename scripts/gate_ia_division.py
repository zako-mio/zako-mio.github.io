#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门控：页面分工（每类内容唯一落点）。读**构建产物 `out/`**，⛔ 不读源码自述。

背景（第三批）：上一版首页把 `WorksExplorer`（全量索引 ＋ 筛选器）整块嵌入，
观测到的实产物读数为「首页与 /works 的作品集合完全相同（10/10，差集为空）」、
「/works 的 93% 文本块出现在首页」。本门控把该分工固化为可复跑判据。

| id | 判据 | 现状基线（改版前 out/） | 目标 |
|---|------|------|------|
| A1 | 首页枚举的作品数（去重详情链接） | 10（＝全部） | ≤ 5 |
| A2 | 首页含索引控件 `filterbar` | 20 | = 0 |
| A3 | 首页含其它页专属区块 `stats__grid` / `about__grid` / `contact__list` | 各 1 | 均 = 0 |
| A4 | 首页 Hero 段承载定位（**对照臂**） | PASS（106 字 / 4 关键词） | ≥60 字 且 ≥1 关键词 |
| A5 | 联系区块唯一落点 `/about` | PASS | ≥1 |
| A6 | 首页可见字符 **防回退棘轮**（含折叠内容） | 改版后 910 → 充实后 1884 | ≥ 1700 |
| A7 | `scripts/gate-manifest.json` 声明自洽（脚本存在／`selftest: true` 者真支持 `--selftest`） | — | 全部成立 |
| A8 | `scripts/` 下符合命名约定的门控**全部已登记**（漏登记 fail-closed） | — | 差集为空 |
| A9 | 首页**非折叠**可见字符棘轮（剥除 `<details>` 全部内容） | 1884 中含折叠 710（37.7%） | ≥ 1100 |
| A10 | **全局公共件（左栏 rail）不得夹带某页专属内容**：每页恰好 1 个 rail；rail 内 ⛔ 无 `filterbar`/`stats__grid`/`about__grid`/`contact__list`；⛔ 无 `/works/<name>` 详情链接 | 第五批新增 | 全部成立 |

阈值推导（⛔ 不由规模直觉）：
  A1 上界 5 = 全量 10 之半。首页职责＝定位，「精选」已裁 3 项（`overrides.json` 的 featured）⇒
     取「全量之半」作为「实质性非全量」的上界，先写死再复测（**预登记**）。
  A2/A3/A5/A7/A8 为**结构判据**（某类区块只能出现在某页／声明与实际必须一致），不涉阈值。
  A4 为**保持性对照臂**：期望改版前后均 PASS，用来证明判据不是恒 FAIL。
  A6 为**棘轮**（ratchet）：阈值取「第三批充实后实测值向下取整到百位」，
     用途是**防回退**，⛔ **不判"内容够不够"** —— 观感充足度属主观裁决，归人
     （见 `03-stage4-verification.md`）。
   A9 为 A6 的**修正判据**：A6 数的是 HTML 文本量，`<details>` 折叠内容也算在内 ⇒
      存在「把内容全折起来而 A6 仍绿」的盲区。A9 剥除 `<details>` 全部内容后计数，
      阈值同样由实测值向下取整（实证：折叠占首页可见字符的 37.7%）。
      ⚠ A9 只防「折叠吃光首屏」，⛔ 仍不判"够不够"。
   A10 为**公共件的越权守卫**（第五批新增）：本批加了「全站常驻左栏」，
      它是**每页都渲染**的公共件 ⇒ 一旦它夹带某页专属区块或详情链接，
      各页的「唯一落点」会被公共件在后台破坏，而 A1–A3 只查首页、看不出来。
      ⇒ 把该纪律前移成结构判据：rail 存在且仅 1 个、rail 内不含三类专属区块，
      也不含详情链接。⚠ 它只管「有没有越权」，⛔ 不判 rail 长得好不好（观感归人）。

用法：
    python3 scripts/gate_ia_division.py                  # 判 out/
    python3 scripts/gate_ia_division.py --root <dir>
    python3 scripts/gate_ia_division.py --selftest       # 合成合规基线逐例变异
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)
STYLE = re.compile(r"<style\b.*?</style>", re.S | re.I)
DETAIL = re.compile(r'href="/works/([a-z0-9\-]+)/?"')
HERO = re.compile(r'<section[^>]*id="top".*?</section>', re.S)
KEYWORDS = ["AI Agent", "机器学习", "运筹优化", "数据科学"]
A1_MAX = 5
A4_MIN_CHARS = 60
# A6 棘轮：第三批充实后，首页可见字符实测 = 1884 ⇒ 向下取整到百位 = 1800（预登记，防回退）
#   ⚠ 该口径**含** <details> 折叠内容（见 A9）
A6_MIN_CHARS = 1800
# A9 棘轮：剥除 <details> 后的非折叠可见字符实测 = 1173 ⇒ 向下取整到百位 = 1100
A9_MIN_CHARS = 1100
DETAILS = re.compile(r"<details\b.*?</details>", re.S | re.I)
# 公共件（左栏 rail）：由 aria-label 锚定，避免误抓页面里别的 <aside>
RAIL = re.compile(r'<aside\b[^>]*class="[^"]*\brail\b[^"]*"[^>]*>(?P<body>.*?)</aside>', re.S | re.I)
RAIL_FORBIDDEN = ("filterbar", "stats__grid", "about__grid", "contact__list")
GATE_NAME_RE = re.compile(r"^(gate_|smoke_).*\.py$")
MANIFEST_REL = Path("scripts") / "gate-manifest.json"

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "out"


def _body(path: Path) -> str:
    """剥 script/style 后再计数：Next 会把 RSC 载荷内联进 <script>，不去除会翻倍计数。"""
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    return STYLE.sub(" ", SCRIPT.sub(" ", raw))


def _hero_text(path: Path) -> str:
    if not path.exists():
        return ""
    match = HERO.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group(0))).strip()


def _visible_chars(path: Path, drop_details: bool = False) -> int:
    """可见字符数（剥 script/style 与标签后，折叠空白再计）。

    `drop_details=True` 时**连 `<details>` 的全部内容一起剥掉** —— 用于度量
    「读者不点开就能看到多少」，避免「把内容全折起来」绕过 A6。
    """
    if not path.exists():
        return 0
    raw = _body(path)
    if drop_details:
        raw = DETAILS.sub(" ", raw)
    text = re.sub(r"<[^>]+>", " ", raw)
    return len(re.sub(r"\s+", " ", text).strip())


def _rail_checks(root: Path) -> list[tuple[str, bool, str]]:
    """A10：全局公共件（左栏 rail）的越权守卫。

    公共件是**每页都渲染**的；它若夹带某页专属区块或详情链接，
    各页的「唯一落点」会被它在后台破坏（A1–A3 只查首页，抓不到）。
    """
    pages = sorted(root.rglob("*.html"))
    if not pages:
        return [("A10", False, f"{root} 下没有 HTML 产物（先跑 pnpm build）")]

    missing: list[str] = []
    duplicated: list[str] = []
    leaked: list[str] = []
    detail_links: list[str] = []

    for page in pages:
        rel = page.relative_to(root).as_posix()
        html = page.read_text(encoding="utf-8", errors="replace")
        rails = RAIL.findall(html)
        if not rails:
            missing.append(rel)
            continue
        if len(rails) > 1:
            duplicated.append(f"{rel}×{len(rails)}")
        body = "\n".join(rails)
        hit = [name for name in RAIL_FORBIDDEN if name in body]
        if hit:
            leaked.append(f"{rel}:{hit}")
        detail = DETAIL.findall(body)
        if detail:
            detail_links.append(f"{rel}:{detail}")

    results = [
        ("A10.rail-present", not missing,
         f"每页恰好 1 个左栏公共件"
         + (" · 缺 rail: " + ", ".join(missing) if missing else "")
         + (" · rail 重复: " + ", ".join(duplicated) if duplicated else "")),
        ("A10.rail-chrome-only", not leaked,
         "左栏未夹带某页专属区块" if not leaked else "左栏越权: " + "; ".join(leaked)),
        ("A10.rail-no-detail-links", not detail_links,
         "左栏无 /works/<name> 详情链接" if not detail_links else "左栏含详情链接: " + "; ".join(detail_links)),
    ]
    # 重复的 rail 并入存在性判据一起判：不额外增添 id，避免判据数量与实现漂移
    if duplicated:
        results[0] = ("A10.rail-present", False, results[0][2])
    return results


def check(root: Path, repo: Path | None = None) -> list[tuple[str, bool, str]]:
    repo = repo or root.parent
    home, works, about = root / "index.html", root / "works" / "index.html", root / "about" / "index.html"
    if not home.exists():
        return [("A0", False, f"{home} 不存在（先跑 pnpm build）")]

    h = _body(home)
    results: list[tuple[str, bool, str]] = []

    home_set = set(DETAIL.findall(h))
    works_set = set(DETAIL.findall(_body(works)))
    n = len(home_set)
    results.append(("A1", n <= A1_MAX,
                    f"首页枚举作品 {n} 项（上界 {A1_MAX}）· 首页集合 {len(home_set)} vs /works {len(works_set)}"))

    c = h.count("filterbar")
    results.append(("A2", c == 0, f"首页 filterbar 计数 {c}（要求 0）"))

    for cls in ("stats__grid", "about__grid", "contact__list"):
        c = h.count(cls)
        results.append((f"A3.{cls}", c == 0, f"首页 {cls} 计数 {c}（要求 0）"))

    text = _hero_text(home)
    kws = [k for k in KEYWORDS if k in text]
    results.append(("A4", len(text) >= A4_MIN_CHARS and len(kws) >= 1,
                    f"Hero 可见文本 {len(text)} 字、方向关键词 {len(kws)} 个（要求 ≥{A4_MIN_CHARS} 字且 ≥1 个）"))

    c = _body(about).count("contact__list")
    results.append(("A5", c >= 1, f"/about contact__list 计数 {c}（要求 ≥1）"))

    vis = _visible_chars(home)
    results.append(("A6", vis >= A6_MIN_CHARS,
                    f"首页可见字符 {vis}（棘轮下限 {A6_MIN_CHARS}，含折叠内容；⛔ 不判内容是否充足）"))

    unfolded = _visible_chars(home, drop_details=True)
    results.append(("A9", unfolded >= A9_MIN_CHARS,
                    f"首页非折叠可见字符 {unfolded}（棘轮下限 {A9_MIN_CHARS}；折叠占 {vis - unfolded}）"))

    results.extend(_rail_checks(root))
    results.extend(_check_manifest(repo))
    return results


def _check_manifest(repo: Path) -> list[tuple[str, bool, str]]:
    """A7/A8：声明式清单与 scripts/ 实际集合必须一致（漏登记即 fail-closed）。"""
    manifest_path = repo / MANIFEST_REL
    if not manifest_path.exists():
        return [("A7", False, f"{MANIFEST_REL} 不存在"),
                ("A8", False, "清单缺失 ⇒ 无法比对 scripts/ 实际集合")]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        declared = [entry["script"] for entry in manifest["gates"]]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return [("A7", False, f"清单解析失败：{exc}"), ("A8", False, "清单不可解析 ⇒ 无法比对")]

    problems: list[str] = []
    for entry in manifest["gates"]:
        path = repo / entry["script"]
        if not path.exists():
            problems.append(f"{entry['script']} 不存在")
            continue
        if entry.get("selftest") and "--selftest" not in path.read_text(encoding="utf-8", errors="replace"):
            problems.append(f"{entry['script']} 声明 selftest:true 但不支持 --selftest")
    results = [("A7", not problems,
                "清单声明自洽（脚本存在 / selftest 声明属实）" if not problems else "；".join(problems))]

    on_disk = {f"scripts/{name}" for name in sorted(p.name for p in (repo / "scripts").iterdir()
                                                    if GATE_NAME_RE.match(p.name))}
    missing = sorted(on_disk - set(declared))
    extra = sorted(set(declared) - on_disk)
    results.append(("A8", not missing and not extra,
                    f"清单登记 {len(declared)} 项 · 实际 {len(on_disk)} 项"
                    + (f" · 漏登记 {missing}" if missing else "")
                    + (f" · 幽灵项 {extra}" if extra else "")
                    + (" · 一致" if not missing and not extra else "")))
    return results


HERO_OK = (
    '<section id="top" class="hero"><h1>zako-mio</h1>'
    "<p>技术同行与开源协作者：聚焦 AI Agent 工程、机器学习建模与运筹优化，"
    "把可复现的工程体系当作交付形态。</p></section>"
)

FILLER = "门控读真实产物，不读源码自述。能力层记录取用后登记消费。" * 80


# 合规的左栏公共件：四路由导航 + 站点标识，⛔ 不含专属区块、不含详情链接
RAIL_OK = '<aside class="rail" aria-label="站点侧栏"><nav><a href="/works">作品</a><a href="/about">关于</a></nav></aside>'


def _compliant_fixture(root: Path) -> None:
    """合成**合规**基线：A1–A10 全 PASS（含清单与 scripts/ 实际集合一致）。"""
    (root / "works").mkdir(parents=True, exist_ok=True)
    (root / "about").mkdir(parents=True, exist_ok=True)
    links = "".join(f'<a href="/works/p{i}/">p{i}</a>' for i in range(10))
    (root / "works" / "index.html").write_text(
        f"<html><body>{RAIL_OK}<div class=\"filterbar\">{links}</div></body></html>", encoding="utf-8")
    (root / "about" / "index.html").write_text(
        f'<html><body>{RAIL_OK}<ul class="contact__list"><li>mail</li></ul></body></html>', encoding="utf-8")
    home = (RAIL_OK + HERO_OK + "".join(f'<a href="/works/p{i}/">p{i}</a>' for i in range(3))
            + f"<footer>{FILLER}</footer>")
    (root / "index.html").write_text(f"<html><body>{home}</body></html>", encoding="utf-8")

    scripts = root.parent / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    declared = ["scripts/gate_alpha.py", "scripts/smoke_beta.py"]
    for rel in declared:
        (root.parent / rel).write_text('"""fixture"""\n# --selftest\n', encoding="utf-8")
    (root.parent / MANIFEST_REL).write_text(
        json.dumps({"schema_version": 1, "note": "fixture",
                    "gates": [{"script": rel, "reads": "x", "selftest": True} for rel in declared],
                    "capability_uses": []}, ensure_ascii=False), encoding="utf-8")


def selftest() -> bool:
    print("== 门控自检（负向夹具：合成合规基线，逐例变异后即恢复）==")
    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "out"
        _compliant_fixture(root)

        base = [r for r in check(root) if not r[1]]
        ok &= not base
        print(f"  [{'PASS' if not base else 'FAIL'}] 对照臂：合成合规样本 FAIL 数 = {len(base)}"
              + (f" · {base}" if base else ""))

        def mutate_and_probe(name: str, relpath: str, transform, criterion: str) -> None:
            nonlocal ok
            path = root / relpath
            original = path.read_text(encoding="utf-8")
            path.write_text(transform(original), encoding="utf-8")
            res = check(root)
            path.write_text(original, encoding="utf-8")
            hit = [r for r in res if not r[1] and r[0].split(".")[0] == criterion]
            ok &= bool(hit)
            print(f"  [{'PASS' if hit else 'FAIL'}] 夹具 {name} 被抓到 :: "
                  + (hit[0][2] if hit else "未触发"))

        mutate_and_probe("A1 首页退化为全量", "index.html",
                         lambda s: s.replace("</body>", "".join(
                             f'<a href="/works/q{i}/">q{i}</a>' for i in range(3)) + "</body>"), "A1")
        mutate_and_probe("A2 首页注入索引控件", "index.html",
                         lambda s: s.replace("</body>", '<div class="filterbar">x</div></body>'), "A2")
        mutate_and_probe("A3 首页注入专属区块", "index.html",
                         lambda s: s.replace("</body>", '<div class="stats__grid about__grid contact__list">x</div></body>'), "A3")
        mutate_and_probe("A4 掏空 Hero 文本", "index.html",
                         lambda s: HERO.sub('<section id="top"></section>', s), "A4")
        mutate_and_probe("A5 /about 联系区块被删", "about/index.html",
                         lambda s: s.replace("contact__list", "x__"), "A5")
        mutate_and_probe("A6 首页被削薄", "index.html",
                         lambda s: s.replace(FILLER, ""), "A6")
        mutate_and_probe("A9 内容被整块折进 details", "index.html",
                         lambda s: s.replace(f"<footer>{FILLER}</footer>",
                                             f"<footer><details>{FILLER}</details></footer>"), "A9")
        mutate_and_probe("A10 左栏夹带别页专属区块", "index.html",
                         lambda s: s.replace("</nav></aside>", '</nav><ul class="contact__list"></ul></aside>'),
                         "A10")
        mutate_and_probe("A10 左栏夹带详情链接", "index.html",
                         lambda s: s.replace("</nav></aside>", '</nav><a href="/works/p0/">p0</a></aside>'),
                         "A10")
        mutate_and_probe("A10 某页缺左栏公共件", "about/index.html",
                         lambda s: s.replace(RAIL_OK, ""), "A10")

        def mutate_file_and_probe(name: str, relpath: str, transform, criterion: str) -> None:
            nonlocal ok
            path = root.parent / relpath
            original = path.read_text(encoding="utf-8")
            path.write_text(transform(original), encoding="utf-8")
            res = check(root)
            path.write_text(original, encoding="utf-8")
            hit = [r for r in res if not r[1] and r[0].split(".")[0] == criterion]
            ok &= bool(hit)
            print(f"  [{'PASS' if hit else 'FAIL'}] 夹具 {name} 被抓到 :: "
                  + (hit[0][2] if hit else "未触发"))

        mutate_file_and_probe("A7 声明指向不存在的脚本", MANIFEST_REL.as_posix(),
                              lambda s: s.replace('"script": "scripts/gate_alpha.py"',
                                                  '"script": "scripts/gate_alpha.py-nope"'), "A7")
        # A8 的真夹具：在 scripts/ 下放一个未登记的门控脚本
        stray = root.parent / "scripts" / "gate_stray.py"
        stray.write_text('"""fixture"""\n', encoding="utf-8")
        res = check(root)
        stray.unlink()
        hit = [r for r in res if not r[1] and r[0] == "A8"]
        ok &= bool(hit)
        print(f"  [{'PASS' if hit else 'FAIL'}] 夹具 A8 漏登记新门控 被抓到 :: "
              + (hit[0][2] if hit else "未触发"))

        restored = [r for r in check(root) if not r[1]]
        ok &= not restored
        print(f"  [{'PASS' if not restored else 'FAIL'}] 恢复后：FAIL 数 = {len(restored)}")

    print(f"\nSELFTEST: {'ALL PASS' if ok else 'HAS FAILURE'}"
          "（每条判据都有能触发它的负向样本）")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--repo", default=str(DEFAULT_ROOT.parent))
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    root = Path(args.root)
    results = check(root, Path(args.repo))
    print(f"== 页面分工门控（读 out/ 实产物；root={root}）==")
    for cid, passed, detail in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {cid}  {detail}")
    ok = all(item[1] for item in results)
    print(f"\nIA-DIVISION: {'ALL PASS' if ok else 'HAS FAILURE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
