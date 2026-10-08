#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收探针（结构类）：页面分工（首页职能 vs 其余页唯一落点）的可机检判据。

判据对象 = **构建产物 `out/`**（⛔ 非源码自述）。计数前先剥 `<script>`/`<style>`
（Next 会把 RSC 载荷内联进 `<script>`，不去除会**翻倍计数** ⇒ 假读）。

| id | 判据 | 目标 | 阈值推导 |
|---|------|------|------|
| A1 | 首页枚举的作品数（去重详情链接） | ≤ 5 | 全量 10；首页职责＝定位，「精选」已裁 3 项 ⇒ 取全量之半 5 为「实质性非全量」上界（**预登记**：先写死再复测） |
| A2 | 首页含索引控件（`filterbar`） | = 0 | 结构判据：explorer 唯一落点 = /works |
| A3 | 首页含其它页专属区块（`stats__grid` / `about__grid` / `contact__list`） | 均 = 0 | 结构判据：每类区块唯一落点 |
| A4 | 首页 Hero 段承载定位（可见文本长度与方向关键词） | ≥60 字 且 ≥1 关键词 | **对照臂**（期望现状即 PASS）：证明判据不是恒 FAIL |
| A5 | 联系区块唯一落点在 /about | ≥1 | 结构判据（与 A3 成对：首页删、/about 存） |

用法（本文件为仓库内**常规复验**用副本；原始件留档于 Mission 目录 batch3-rd/probe/）：
    python3 scripts/probes/acceptance_probe.py [--root <out目录>]   # 判真实产物
    python3 scripts/probes/acceptance_probe.py --selftest           # 负向夹具自检
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]

SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)
STYLE = re.compile(r"<style\b.*?</style>", re.S | re.I)
DETAIL = re.compile(r'href="/works/([a-z0-9\-]+)/?"')
HERO = re.compile(r'<section[^>]*id="top".*?</section>', re.S)
KEYWORDS = ["AI Agent", "机器学习", "运筹优化", "数据科学"]
A1_MAX = 5
A4_MIN_CHARS = 60


def body(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return STYLE.sub(" ", SCRIPT.sub(" ", raw))


def hero_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    match = HERO.search(raw)
    if not match:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group(0))).strip()


def check(root: Path):
    home, works, about = root / "index.html", root / "works" / "index.html", root / "about" / "index.html"
    if not home.exists():
        return [("A0", "FAIL", f"{home} 不存在")]

    h = body(home)
    results = []

    home_set = set(DETAIL.findall(h))
    works_set = set(DETAIL.findall(body(works))) if works.exists() else set()
    n = len(home_set)
    results.append(("A1", "PASS" if n <= A1_MAX else "FAIL",
                    f"首页枚举作品 {n} 项（上界 {A1_MAX}）；首页 {len(home_set)} vs /works {len(works_set)}"))

    c = h.count("filterbar")
    results.append(("A2", "PASS" if c == 0 else "FAIL", f"首页 filterbar 计数 {c}（要求 0）"))

    for cls in ("stats__grid", "about__grid", "contact__list"):
        c = h.count(cls)
        results.append((f"A3.{cls}", "PASS" if c == 0 else "FAIL", f"首页 {cls} 计数 {c}（要求 0）"))

    text = hero_text(home)
    kws = [k for k in KEYWORDS if k in text]
    ok = len(text) >= A4_MIN_CHARS and len(kws) >= 1
    results.append(("A4", "PASS" if ok else "FAIL",
                    f"Hero 可见文本 {len(text)} 字、方向关键词 {len(kws)} 个（要求 ≥{A4_MIN_CHARS} 字且 ≥1 个）"))

    a = body(about) if about.exists() else ""
    c = a.count("contact__list")
    results.append(("A5", "PASS" if c >= 1 else "FAIL", f"/about contact__list 计数 {c}（要求 ≥1）"))
    return results


HERO_OK = ('<section id="top" class="hero"><h1>zako-mio</h1>'
           '<p>技术同行与开源协作者：聚焦 AI Agent 工程、机器学习建模与运筹优化，'
           '把可复现的工程体系当作交付形态。</p></section>')


def compliant_fixture(root: Path):
    """合成**合规**基线：A1–A5 全 PASS。"""
    (root / "works").mkdir(parents=True, exist_ok=True)
    (root / "about").mkdir(parents=True, exist_ok=True)
    links = "".join(f'<a href="/works/p{i}/">p{i}</a>' for i in range(10))
    (root / "works" / "index.html").write_text(f'<html><body><div class="filterbar">{links}</div></body></html>', encoding="utf-8")
    (root / "about" / "index.html").write_text('<html><body><ul class="contact__list"><li>mail</li></ul></body></html>', encoding="utf-8")
    home = HERO_OK + "".join(f'<a href="/works/p{i}/">p{i}</a>' for i in range(3)) + '<footer>as_of</footer>'
    (root / "index.html").write_text(f"<html><body>{home}</body></html>", encoding="utf-8")


def selftest() -> int:
    print("== 负向夹具自检（合成合规基线，逐例变异后即恢复）==")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "out"
        compliant_fixture(root)

        base = check(root)
        base_fails = [r for r in base if r[1] == "FAIL"]
        print(f"  [{'PASS' if not base_fails else 'FAIL'}] 对照臂：合成合规样本 FAIL 数 = {len(base_fails)}"
              + (f" · {base_fails}" if base_fails else ""))

        def mutate_and_probe(name, relpath, transform, criterion):
            path = root / relpath
            original = path.read_text(encoding="utf-8")
            path.write_text(transform(original), encoding="utf-8")
            res = check(root)
            path.write_text(original, encoding="utf-8")
            hit = [r for r in res if r[1] == "FAIL" and r[0].split(".")[0] == criterion]
            print(f"  [{'PASS' if hit else 'FAIL'}] 夹具 {name} 被抓到 :: "
                  + (hit[0][2] if hit else "未触发"))

        mutate_and_probe("A1 首页退化为全量", "index.html",
                         lambda s: s.replace("</body>", "".join(f'<a href="/works/q{i}/">q{i}</a>' for i in range(3)) + "</body>"), "A1")
        mutate_and_probe("A2 首页注入索引控件", "index.html",
                         lambda s: s.replace("</body>", '<div class="filterbar">x</div></body>'), "A2")
        mutate_and_probe("A3 首页注入专属区块", "index.html",
                         lambda s: s.replace("</body>", '<div class="stats__grid about__grid contact__list">x</div></body>'), "A3")
        mutate_and_probe("A4 掏空 Hero 文本", "index.html",
                         lambda s: HERO.sub('<section id="top"></section>', s), "A4")
        mutate_and_probe("A5 /about 联系区块被删", "about/index.html",
                         lambda s: s.replace("contact__list", "x__"), "A5")

        restored = [r for r in check(root) if r[1] == "FAIL"]
        print(f"  [{'PASS' if not restored else 'FAIL'}] 恢复后：FAIL 数 = {len(restored)}")
    print("\nSELFTEST: done")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO_ROOT / "out"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    root = Path(args.root)
    results = check(root)
    print(f"== 验收探针（root={root}）==")
    for rid, st, msg in results:
        print(f"  [{st}] {rid} {msg}")
    fails = [r for r in results if r[1] == "FAIL"]
    print(f"\n{len(results) - len(fails)}/{len(results)} PASS" + (f" · FAIL {len(fails)} 条" if fails else " · ALL PASS"))
    print(f"\nACCEPTANCE: {'ALL PASS' if not fails else 'FAIL'}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
