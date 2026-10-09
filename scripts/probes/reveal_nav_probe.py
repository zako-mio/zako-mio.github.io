#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""进场可见性 × 进入路径 探针：`[data-reveal]` 的**可见终态必须与「怎么进来的」无关**。

# ─────────────────────────────────────────────────────────────────────────────
# 来源登记（Provenance）：本件是 scripts/probes/ 下的 **CI 活件**（可演进）。
#   · 仓库原生（repo-native）：来源即本仓库，无归档副本。
#   · 登记表：scripts/probes/PROVENANCE.json（机检 scripts/probes/check_provenance.py）
#   · 出土缺陷（第十二批，用户实测报障）：动效开时
#       ① `/` →（客户端点击）→ `/about` ⇒ 关于页 8 个 section 全部 `opacity:0 / is-in=false`
#       ② 再点回 `/` ⇒ 首页 `#featured`/`#build-notes`/`#directory` 同样全灭
#     根因：`MotionRuntime` 挂在**根布局**上、跨客户端路由常驻，而 `useEffect(…, [])`
#     全生命周期只跑一次 ⇒ 首次扫描之后新挂载的 `[data-reveal]` 从未被 observe
#     ⇒ 永久停在 `html.js-motion [data-reveal]{opacity:0}` 的隐藏态。
#   · 为什么必须单列一条：八闸**只读静态产物**（哪份 HTML 里 `[data-reveal]` 都齐全），
#     四条浏览器探针**各自单页整页加载**、从不做跨路由导航 ⇒ 这个作用面**无人在看**。
#     ⇒ 判据对象＝**进入路径**这一维，而不是任何单个页面的形态。
# ─────────────────────────────────────────────────────────────────────────────

判据（fail-closed）：
  J1 **整页加载臂**：进入的每个路由，其 `[data-reveal]` 走完滚动后全部可见；
  J2 **客户端导航臂**：同上，但用站内 `<Link>` 点击进入（⛔ 不是 `goto`）；
  J3 **路径无关性**：两臂在**同一路由**上的判据对象集合与可见性必须逐项一致。
  ⚠ 判据对象**从产物派生**（home 的在站链接去重 ⇒ 再筛「有 `[data-reveal]` 的路由」），
    ⛔ 不写路由/选择器字面量清单（那会随改版静默腐化）。
  ⛔ 总数 0 ⇒ 判 FAIL（判据在此哑火，不得静默通过）。

⚠ **声明的不覆盖面**：候选路由只取「无 `target`/`download` 的同 origin 链接」。
  线上本站与各项目站同 origin（`zako-mio.github.io/<name>/`），故**不能**靠「跨域」判外链 ——
  排除靠 `target`/`download` 属性这一**书写形态**；若日后新增同 origin 的项目站直链（不带 target），
  本探针会把它当路由去点并在 `wait_for_function` 上超时 ⇒ 属**已知假 FAIL 形态**，届时按属性补排除规则。
  ⛔ 不得改成按 href 前缀/项目名字面量排除（会随改版腐化）。

用法：
    setsid python3 -m http.server 4399 --directory out >/tmp/…log 2>&1 </dev/null & disown
    python3 scripts/probes/reveal_nav_probe.py                  # 实测 out/
    python3 scripts/probes/reveal_nav_probe.py --selftest       # 活 DOM 上复原缺陷，验判据非恒真
    SITE_BASE=http://127.0.0.1:4400 python3 scripts/probes/reveal_nav_probe.py
    python3 scripts/probes/reveal_nav_probe.py https://zako-mio.github.io   # ★ 上线后对生产站点复验
      （⚠ 指生产 origin 时会把「项目站同 origin」纳入视野，故必须靠 target/download 属性排除外链；
        见 ROUTES_JS 头注。这是「上线后复验」直接可跑的那一条。）
⛔ 只读页面，不改仓库。

⚠ 实测口径两条（都是首版踩过的假 FAIL）：
   ① 滚动必须 `behavior:'instant'`：站点 `html{scroll-behavior:smooth}` 会让「循环里发出的
      目标 y」与「真实滚动位置」脱钩，未真正进入视口的节点永远不会被 reveal；
   ② 读数须等**错峰延迟 ＋ `--dur-4`** 走完（`--i*70ms` 可叠到数百毫秒），故滚动后另留 1.5s。
"""
from __future__ import annotations

import argparse
import os
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_BASE = "http://127.0.0.1:4399"
VISIBLE_MIN = 0.99
ENTRY = "/"

# 量当前文档里全部 `[data-reveal]` 的终态。键＝`id`（无 id 时用文档序位），⛔ 键不得依赖外部清单。
MEASURE_JS = r"""
() => {
  const out = {};
  document.querySelectorAll('[data-reveal]').forEach((el, i) => {
    const key = el.id ? `#${el.id}` : `${el.tagName.toLowerCase()}[${i}]`;
    const cs = getComputedStyle(el);
    out[key] = {
      opacity: parseFloat(cs.opacity),
      display: cs.display,
      visibility: cs.visibility,
      isIn: el.classList.contains('is-in'),
    };
  });
  return out;
}
"""

# 从首页的**站内链接**派生候选路由，⛔ 不写死路由清单。
# 返回 [{path, href}]：`href` 是**产物里的原样写法**（点名要用它 —— 本项目同一路由存在
# `/works` 与 `/works/` 两种写法，用前缀匹配会点到 `/works/<name>/` 上去）。
#
# ★ 必须排除 `target` / `download` 链接（第十二批实跑所得，CI 里看不到）：
#   本站（`zako-mio.github.io`）与各**项目站**（`zako-mio.github.io/<name>/`）**同 origin**，
#   故「跨域即外链」这条判据在**线上**失效 —— 卡片页脚的「在线预览」是 `target="_blank"`，
#   点它会开新标签页、当前页 pathname 永不变化 ⇒ 探针超时（本该只读的判据通道被带偏）。
#   ⛔ 不要改成「按 href 前缀排除 /works/」：那是把项目名当字面量写进判据（会腐化）。
ROUTES_JS = r"""
() => {
  const seen = new Map();
  document.querySelectorAll('a[href]').forEach((a) => {
    if (a.hasAttribute('target') || a.hasAttribute('download')) return;  // 新标签页/下载 ⇒ 非路由
    const raw = a.getAttribute('href');
    let u;
    try { u = new URL(raw, location.origin); } catch (e) { return; }
    if (u.origin !== location.origin) return;
    if (u.pathname === '/') return;
    if (!seen.has(u.pathname)) seen.set(u.pathname, raw);
  });
  return [...seen].map(([path, href]) => ({ path, href })).sort((a, b) => a.path.localeCompare(b.path));
}
"""

SCROLL_JS = r"""
async () => {
  const h = document.body.scrollHeight;
  const step = Math.max(200, Math.round(h / 12));
  for (let y = 0; y <= h; y += step) {
    window.scrollTo({ top: y, behavior: 'instant' });
    await new Promise((r) => setTimeout(r, 120));
  }
  window.scrollTo({ top: h, behavior: 'instant' });
  await new Promise((r) => setTimeout(r, 600));
  window.scrollTo({ top: 0, behavior: 'instant' });
  await new Promise((r) => setTimeout(r, 1500));
}
"""

# ★ 负向夹具：把「持续接管」中掉 —— 只废掉 `observe(document.body, {subtree, childList})`
#   这一种调用（等价于修复前的「挂载时扫描一次」），⛔ 不动 BackdropFx 观察 documentElement 属性那个。
KILL_TAKEOVER_JS = r"""
(() => {
  const Native = window.MutationObserver;
  window.MutationObserver = class extends Native {
    observe(target, options) {
      const o = options || {};
      if (target === document.body && o.subtree && o.childList && !o.attributes) return;
      return super.observe(target, options);
    }
  };
})();
"""


def visible(rec: dict) -> bool:
    return rec["opacity"] >= VISIBLE_MIN and rec["display"] != "none" and rec["visibility"] != "hidden"


def new_page(browser, *, kill_takeover: bool = False):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
    # 动效「开」＝显式要求（覆盖 OS reduce）⇒ 隐藏态必定生效，判据才有对象。
    ctx.add_init_script("try{localStorage.setItem('ui-motion','on')}catch(e){}")
    if kill_takeover:
        ctx.add_init_script(KILL_TAKEOVER_JS)
    return ctx, ctx.new_page()


def full_load_arm(page, base: str, routes: list[dict]) -> dict[str, dict]:
    maps: dict[str, dict] = {}
    for r in [{"path": ENTRY, "href": ENTRY}] + routes:
        page.goto(f"{base}{r['path']}", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.evaluate(SCROLL_JS)
        maps[r["path"]] = page.evaluate(MEASURE_JS)
    return maps


def client_nav_arm(page, base: str, routes: list[dict], inspect: set[str]) -> dict[str, dict]:
    """从首页出发，逐个点击进入再点回首页 —— 全程只用站内 `<Link>`（⛔ 不含 goto）。

    `inspect` ＝「整页加载臂里有 `[data-reveal]` 的路由」：只有它们值得走完整滚动；
    其余路由仍然**照走一遍**（覆盖「中途经过无 `[data-reveal]` 的页」这条路径，即
    修复前 `nodes.length === 0` 提前 return 的那一半缺陷），但不必扫全页滚动。
    """
    maps: dict[str, dict] = {}
    page.goto(f"{base}{ENTRY}", wait_until="networkidle")
    page.wait_for_timeout(500)
    page.evaluate(SCROLL_JS)
    maps[ENTRY] = page.evaluate(MEASURE_JS)

    for r in routes:
        link = page.locator(f"a[href='{r['href']}']:visible").first
        if link.count() == 0:
            print(f"  [SKIP] 客户端导航臂：页面上没有可见的站内链接 → {r['path']}（原样 href={r['href']!r}）")
            continue
        link.click()
        # ⚠ 本项目同一路由有 `/works` 与 `/works/` 两种写法（后者会 302/客户端重定向到前者），
        #   故按**归一化 pathname**等待，⛔ 不用精确 URL 比较（会假超时）。
        page.wait_for_function(
            "(p) => location.pathname.replace(/\\/+$/, '') === p || location.pathname === p + '/'",
            arg=r["path"].rstrip("/"), timeout=15000,
        )
        page.wait_for_timeout(800)
        entries = page.evaluate("performance.getEntriesByType('navigation').length")
        if entries != 1:
            print(f"  [WARN] {r['path']}：navigation entries={entries} ⇒ 其实是整页加载，本臂不成立")
        if r["path"] in inspect:
            page.evaluate(SCROLL_JS)
        else:
            page.wait_for_timeout(400)
        maps[r["path"]] = page.evaluate(MEASURE_JS)

        back = page.locator(f"a[href='{ENTRY}']:visible").first
        back.click()
        page.wait_for_function("() => location.pathname === '/'", timeout=15000)
        page.wait_for_timeout(800)
        # 每一次「切回首页」都是一个独立的回归点（原缺陷的第二个症状），故逐次复测。
        page.evaluate(SCROLL_JS)
        maps[ENTRY] = page.evaluate(MEASURE_JS)
    return maps


def judge(arm: str, maps: dict[str, dict]) -> list[str]:
    fails: list[str] = []
    for route, recs in maps.items():
        if not recs:
            print(f"  [SKIP] {arm} {route}：该路由无 `[data-reveal]`（无判据对象）")
            continue
        bad = [k for k, v in recs.items() if not visible(v)]
        print(f"  [{'PASS' if not bad else 'FAIL'}] {arm} {route}：{len(recs)} 个 `[data-reveal]`"
              + ("" if not bad else f" ⇒ 不可见 {len(bad)} 个：{', '.join(bad[:4])}…"))
        if bad:
            for k in bad[:6]:
                fails.append(f"{arm} {route} {k} opacity={recs[k]['opacity']} is-in={recs[k]['isIn']}")
    return fails


def diff_fails(full: dict[str, dict], nav: dict[str, dict]) -> list[str]:
    out: list[str] = []
    for route, recs in full.items():
        if route not in nav:
            continue
        other = nav[route]
        for k in sorted(set(recs) | set(other)):
            a, b = recs.get(k), other.get(k)
            if a is None or b is None:
                out.append(f"J3 {route} {k}：两臂判据对象集合不一致（整页={a is not None} 客户端={b is not None}）")
            elif visible(a) != visible(b):
                out.append(f"J3 {route} {k}：可见性随进入路径变化（整页={visible(a)} 客户端={visible(b)}）")
    return out


def run(base: str) -> int:
    fails: list[str] = []
    compared = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()

        ctx, page = new_page(browser)
        page.goto(f"{base}{ENTRY}", wait_until="networkidle")
        page.wait_for_timeout(400)
        attr = page.evaluate("document.documentElement.getAttribute('data-motion')")
        if attr != "on":
            print(f"  [FAIL] 前置条件不成立：data-motion={attr!r}（期望 'on'）—— 隐藏态未生效，判据无对象")
            ctx.close()
            browser.close()
            return 1

        routes = page.evaluate(ROUTES_JS)
        print(f"== 候选路由（由首页站内链接派生）：{[r['path'] for r in routes]} ==")

        print("\n-- 臂 1：整页加载（goto）--")
        full = full_load_arm(page, base, routes)
        fails += judge("整页", full)

        # 判据对象由产物派生：只有整页加载臂里真有 `[data-reveal]` 的路由才值得整页滚动。
        inspect = {r["path"] for r in routes if full.get(r["path"])}
        print(f"== 有判据对象的路由：{sorted(inspect)} ==")

        print("\n-- 臂 2：客户端导航（点击站内 <Link>）--")
        nav = client_nav_arm(page, base, routes, inspect)
        fails += judge("客户端", nav)

        print("\n-- J3：进入路径无关性 --")
        d = diff_fails(full, nav)
        for x in d:
            print(f"  [FAIL] {x}")
        fails += d
        if not d:
            print("  [PASS] 两臂逐项一致")

        compared = sum(len(v) for v in full.values()) + sum(len(v) for v in nav.values())

        ctx.close()
        browser.close()

    if compared == 0:
        print("\n  [FAIL] 判据在此哑火：两臂合计判据对象为 0")
        fails.append("空集")
        return 1
    print(f"\n判据对象读数：{compared} 项")
    print("\nREVEAL-NAV: " + ("ALL PASS" if not fails else f"HAS FAILURE ({len(fails)})"))
    return 0 if not fails else 1


# ---------------------------------------------------------------- selftest
def selftest(base: str) -> int:
    checks: list[tuple[str, bool]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # 夹具 N1：复原批十二缺陷（中掉「持续接管」），客户端 `/` → `/about/` 必须被抓到。
        ctx, page = new_page(browser, kill_takeover=True)
        page.goto(f"{base}{ENTRY}", wait_until="networkidle")
        page.wait_for_timeout(400)
        routes = page.evaluate(ROUTES_JS)
        route = next((r for r in routes if r["path"].rstrip("/").endswith("/about")), None)
        if route is None:
            route = next((r for r in routes if r["path"] in ("/stats/", "/works/")), routes[0] if routes else None)
        if route is None:
            checks.append(("夹具 N1：页面上找不到任何站内路由可点", False))
            ctx.close()
            browser.close()
            print("== selftest（活 DOM 上复原缺陷；⛔ 不改仓库）==")
            for name, ok in checks:
                print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
            print("  SELFTEST: FAIL（夹具前置条件不成立）")
            return 1

        page.locator(f"a[href='{route['href']}']:visible").first.click()
        page.wait_for_url(f"{base}{route['path']}", timeout=15000)
        page.wait_for_timeout(800)
        page.evaluate(SCROLL_JS)
        recs = page.evaluate(MEASURE_JS)
        hits = [k for k, v in recs.items() if not visible(v)]
        checks.append((f"夹具 N1（中掉接管 ⇒ 客户端导航到 {route['path']} 后内容不可见）被抓到",
                       bool(recs) and bool(hits)))
        n1_control = bool(recs)
        ctx.close()

        # 夹具 N2：运行中**动态插入**新的 `[data-reveal]`（ProjectCard 那一类），
        #          在接管被中掉时须被判为不可见；接管正常时须变为可见（正对照）。
        def late_insert(kill: bool) -> tuple[bool, bool]:
            c, pg = new_page(browser, kill_takeover=kill)
            pg.goto(f"{base}{ENTRY}", wait_until="networkidle")
            pg.wait_for_timeout(500)
            pg.evaluate("""async () => {
                const s = document.createElement('section');
                s.id = 'selftest-late-insert';
                s.setAttribute('data-reveal', '');
                s.innerHTML = '<p>late insert</p>';
                document.querySelector('main').appendChild(s);
                // ⚠ 必须把它滚进视口：判据是「新节点能被接管并在进入视口时 reveal」，
                //   ⛔ 不是「任意位置的新节点都必须立刻可见」（那会误杀正常的进场语义）。
                s.scrollIntoView({ block: 'center', behavior: 'instant' });
                await new Promise((r) => setTimeout(r, 1500));
            }""")
            pg.wait_for_timeout(400)
            got = pg.evaluate(MEASURE_JS).get("#selftest-late-insert")
            c.close()
            return got is not None, (visible(got) if got else False)

        present_killed, vis_killed = late_insert(True)
        checks.append(("夹具 N2（中掉接管 ⇒ 运行中插入的 `[data-reveal]` 不可见）被抓到",
                       present_killed and not vis_killed))
        present_live, vis_live = late_insert(False)
        checks.append(("正对照（接管在办 ⇒ 运行中插入的 `[data-reveal]` 变可见）",
                       present_live and vis_live))
        checks.append(("前置守卫：夹具跑在真有 `[data-reveal]` 的页面上", n1_control))

        browser.close()

    print("== selftest（活 DOM 上复原缺陷；⛔ 不改仓库）==")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    good = all(ok for _, ok in checks)
    print("  SELFTEST:", "PASS" if good else "FAIL（判据可能恒真）")
    return 0 if good else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="进场可见性 × 进入路径（整页加载 vs 客户端路由）")
    ap.add_argument("base", nargs="?", default=None,
                    help=f"站点基址（缺省 {DEFAULT_BASE}；亦可由 SITE_BASE 环境变量给出）")
    ap.add_argument("--selftest", action="store_true",
                    help="在活 DOM 上复原被修掉的缺陷，验证判据非恒真")
    args = ap.parse_args()
    base = (args.base or os.environ.get("SITE_BASE") or DEFAULT_BASE).rstrip("/")

    if args.selftest:
        return selftest(base)
    return run(base)


if __name__ == "__main__":
    raise SystemExit(main())
