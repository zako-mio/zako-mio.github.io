#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""布局稳定性探针（B1，第十八批）。

为什么需要它（**这条判据的存在理由**）：
    本站的进场动效（`rise-in` / `reveal-in`）**走 `translate` 属性** —— 这是**合成层**动画，
    不触发 layout，因此**不会被 CLS 计入**（这是有意的设计）。
    但「有意」与「实际」是两回事：任何一次改动（新增异步块、字体度量变化、图片无尺寸、
    浮层定位变化、主题切换里混入尺寸变化）都可能引入**真·布局位移**，而既有 8 闸 ＋ 10 探针
    **没有一条在看这件事**：
      · `gate_motion_budget` 只看**动效预算**（时长/infinite/兜底窗口），⛔ 不量位移；
      · `svg_layout_probe` 只看图件内部几何，⛔ 不看整页；
      · `surface_hit` / `hero_hit` 只看命中与热区，⛔ 不看位移。
    ⇒ 这是**判据的空白面**（同型教训见 b127：空白面会长期掩盖缺陷）。
    本探针把「布局稳定性」做成可复跑的机检 —— 它同时是用户轴 B（**所见符合所得**）在
    「时间维度」上的形态：**看到的东西不该自己动**。

判据（L1–L5；两条通道：PerformanceObserver 的 layout-shift ＋ 几何快照差分）
| id | 判据 | 目标 |
|----|------|------|
| L1 | **加载期 CLS**：每路由从导航开始到「稳定窗口」结束的 `layout-shift` 累积值（只计非用户输入引起者） | ≤ 0.1 |
| L2 | **滚动期 CLS**：整页滚动（分步到底）后再读同一累积值的**增量** | ≤ 0.1 |
| L3 | **主题切换（light→dark）几何零位移**：两次快照间只有主题这一维变化，比较 `<main>` 内可见非定位元素的 **layout box** | max\\|Δ\\| ≤ 0.5px 且集合一致 |
| L4 | **动效开关（on→off）几何零位移**：同上 | max\\|Δ\\| ≤ 0.5px 且集合一致 |
| L5 | **非空守卫**：追踪集元素数 ≥ 20 且 CLS 观察器已挂载（`__ls.error` 为空） | 成立 |

★★ **量的是「布局位置」（rect，亚像素），但快照期把「进场位移」归一化掉** ——
    `translate` 是**合成层**属性、**不进布局**，却**会进 `getBoundingClientRect`**。
    实测踩到：`data-motion='off'` 时 `:root[data-motion='off'] [data-reveal]{translate:none!important}`
    去掉 16px 的进场偏移 ⇒ `/` 与 `/about/` 各有 **144/136 件「位移 16px」**，
    而 `translate` **不进布局、也不被 CLS 计入** ⇒ 那是**正常行为**，不是缺陷。
    ⇒ 本探针在两次快照里**都**临时把 `[data-reveal]` 的 `translate` 清零（差异抵消，量到布局位置）；
    ⛔ 不可全局清零 transform —— 站内 `.hero__map` 的**居中**正是 `translate: 0 -50%`，
    全局清零会把居中一起吃掉（该坑批十三已记录）。
    ⚠ 另一条**走不通**的路（实测否决）：改用 `offsetTop/offsetLeft` 累加以求天然 transform-free
    —— 但 `offsetTop` 是**整数**且基准是**动态 `offsetParent`**（动画期带 transform 的祖先会成为
    offsetParent、动效关掉后不再是）⇒ 基准变化会让累加值差 1px，而分数级 rect **逐位相同**
    （实测 525.6563 不变）⇒ 那个 1px 是**量化伪影**，不是位移。
★ **`.chart__frame` 子树被排除**：本站图表是**双模帧**（明/暗各一份，深浅切换显隐互换），
    那是**有意**的可见性切换，由 `gate_theme_states` 单独管；本探针不判「哪一帧被显示」。
    实测：不排除时 `/stats` 会在主题切换处报 **58 个元素的集合差异**，全部落在 `.chart__frame` 内。

阈值推导（⛔ 不由规模直觉）：
  L1/L2 取 **0.1** —— 这是 **Google Core Web Vitals 的公开「good」上界**（外部权威口径，
    非本站自拟）；本站**先写死再实测**（预登记）。⚠ 若实测超出，处置是**查位移来源**，
    ⛔ 不是把阈值放宽（放宽阈值＝把判据变成装饰）。
  L3/L4 取 **0.5px** —— 亚像素渲染/四舍五入的容差；取半像素是「比一个设备像素更严」的
    整数约定，仍能抓住任何**真实**的位移（真实位移按像素起跳）。
  L5 取 **20** —— 追踪集是 `<main>` 内的可见静态元素；本站 5 条受检路由最少的 `/works`
    主体也远超 20。⚠ 它**不是**充分性判据（20 个元素不能代表全页），只兜「快照机制哑火」。

⛔ 不覆盖面（如实声明）：
  ① ⛔ 不判**动画期**的位移（进场动画本就在动，且不触发 layout）——本探针在**动画落定后**才快照；
  ② ⛔ 不判懒加载/后台更新引起、但发生在观测窗口之外的位移；
  ③ ⛔ 不判观感（「位移多少算难看」归人）——只判上述可算量；
  ④ 受检路由＝5 条（与 `axe_a11y_probe` 同集合），⛔ 不主张覆盖全站 15 路由；
  ⑤ L3/L4 每路由各测**一个方向**（light→dark、on→off），⛔ 不主张覆盖全部三态循环组合；
  ⑥ ⛔ 不判 transform/合成层位移（见上「量的是 layout box」）——那类由 `gate_motion_budget` 与
     四臂熔断（`batch13-evidence/verify_fd1.py`）分管。

用法：
    setsid python3 -m http.server 4399 --directory out >/tmp/…log 2>&1 </dev/null & disown
    python3 scripts/probes/layout_stability_probe.py
    python3 scripts/probes/layout_stability_probe.py --out <留档目录>
    python3 scripts/probes/layout_stability_probe.py --selftest    # 合成夹具，验证判据非恒真
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_BASE = "http://127.0.0.1:4399"

# 受检路由（与 axe_a11y_probe 同集合；⛔ 不主张全站覆盖）
ROUTES = ["/", "/works/", "/about/", "/stats/", "/works/12-factor-methodology-kg/"]

CLS_BUDGET = 0.1        # L1/L2：Core Web Vitals「good」上界（预登记）
RECT_TOL = 0.5          # L3/L4：亚像素容差
MIN_TRACKED = 20        # L5：追踪集下界
SETTLE_MS = 1800        # 等进场动画落定后再快照（⛔ 不在动画期判位移）

# ★ CLS 观察器必须在**页面脚本之前**注入（否则漏掉早期位移）——用 add_init_script。
CLS_INIT = r"""
window.__ls = { value: 0, entries: 0, sources: 0, error: null };
try {
  new PerformanceObserver(function (list) {
    list.getEntries().forEach(function (e) {
      if (e.hadRecentInput) return;
      window.__ls.value += e.value;
      window.__ls.entries += 1;
      window.__ls.sources += (e.sources || []).length;
    });
  }).observe({ type: 'layout-shift', buffered: true });
} catch (err) { window.__ls.error = String(err); }
"""

# 给 `<main>` 内元素打一次性索引（跨快照以同一 idx 配对）。
# ⚠ **必须排除 `.chart__frame` 子树**：本站图表是**双模帧**（明/暗各一份，深浅切换时显隐互换）
#   ⇒ 它是**有意**的可见性切换，由 `gate_theme_states` 单独管；本探针判的是「位置与尺寸的稳定性」，
#   不判「哪一帧被显示」（判据的作用面必须＝被判对象）。
TAG_JS = r"""
() => {
  const main = document.querySelector('main');
  if (!main) return 0;
  let n = 0;
  main.querySelectorAll('*').forEach(function (el) {
    // ⛔ 只追踪 **HTMLElement**：SVG 元素**没有** `offsetLeft/offsetParent`（取值为 undefined
    //   ⇒ 累加出 NaN，实测踩到）。SVG 的**内部几何**由 `svg_layout_probe` 单独管；它的
    //   HTML 容器（`.figure` / `.card` 等）仍在本追踪面内 ⇒ 尺寸变化依旧可测。
    if (!(el instanceof HTMLElement)) return;
    if (el.closest('.chart__frame')) return;
    if (!el.hasAttribute('data-ls-idx')) { el.setAttribute('data-ls-idx', String(n)); }
    n += 1;
  });
  return n;
}
"""

# 布局几何快照：只取「可见、非 fixed/sticky、有尺寸」者。
# ★★ 用 `getBoundingClientRect`（**亚像素**），但**先把「进场位移」归一化**：
#    `translate` 是**合成层**属性、**不进布局**，却**会进 rect** ⇒ 不归一化的话，
#    `data-motion='off'` 的规则 `[data-reveal]{translate:none!important}`（去掉 16px 进场偏移）
#    会让 `/` 与 `/about/` 各有 144/136 件「位移 16px」，而那是**正常行为**、不是 reflow
#    （实测：动效切换期间 `layout-shift` 事件为空）。⇒ 快照期临时把 `[data-reveal]` 的
#    `translate` 清零，**两次快照都做** ⇒ 差异抵消，量到的就是**布局位置**。
#    ⚠ 只清零 `[data-reveal]`：站内其它 transform 是**静止**的（如 `.hero__map` 的 `translate: 0 -50%`
#      居中），两态相同、自然抵消；⛔ 不可全局清零 transform —— 会连同**居中**一起吃掉（实测过的坑）。
# ⚠ 早前版本改走 `offsetTop/offsetLeft` 累加（想天然 transform-free），实测**不可用**：
#    `offsetTop` 是**整数**、且基准是**动态的 `offsetParent`**（`.hero__inner > *` 在动画期带
#    transform ⇒ 会成为 offsetParent；动效关掉后不再是）⇒ 基准变短/变长会让累加值差 1px，
#    而分数级 rect 实测**逐位相同**（525.6563 不变）⇒ 那 1px 是**量化伪影**，不是位移。
# ★★ **必须换算成「文档坐标」**（`+ window.scrollX/scrollY`）：`getBoundingClientRect` 是
#    **视口相对**，而 `page.click()` 会**自动把目标滚进视口**、且站点在动效开时走 `scroll-behavior`
#    ⇒ 快照可能落在**滚动进行中的不同位置**，把滚动量记成「位移」（实测踩到：`/works` 的 L4
#    在 5 次全量跑里挂 2 次，位移值随机为 **17px / 365px**，而追踪集完全一致 ⇒ 典型滚动伪影）。
#    文档坐标对滚动**不变**，从根上消掉这一类抖动。
SNAP_JS = r"""
() => {
  const main = document.querySelector('main');
  if (!main) return {};
  const st = document.createElement('style');
  st.textContent = '[data-reveal]{translate:none !important;}';
  document.head.appendChild(st);
  const sx = window.scrollX, sy = window.scrollY;
  const out = {};
  document.querySelectorAll('main [data-ls-idx]').forEach(function (el) {
    if (!(el instanceof HTMLElement)) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    if (cs.position === 'fixed' || cs.position === 'sticky') return;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    out[el.getAttribute('data-ls-idx')] = [
      +(r.x + sx).toFixed(2), +(r.y + sy).toFixed(2), +r.width.toFixed(2), +r.height.toFixed(2)
    ];
  });
  document.head.removeChild(st);
  return out;
}
"""

# ⚠ 站内 `<button class="theme-toggle">` 有**两个**（轨道处的常驻件 ＋ 另一处），
#   其中只有一个在 1440px 档可见 ⇒ 必须用 `:visible` 限定，否则 click 会命中被隐藏的那个
#   （实测踩到：Timeout，element is not visible）。
THEME_BTN = 'button[aria-label^="配色主题"]:visible'
MOTION_BTN = 'button[aria-label^="动效"]:visible'


def read_cls(page) -> dict:
    return page.evaluate("() => window.__ls || { error: 'no observer' }")


def snap(page) -> dict:
    return page.evaluate(SNAP_JS)


def diff_snaps(a: dict, b: dict) -> tuple[float, list[str], bool]:
    """返回 (max|Δ|, 集合差异说明, 集合是否一致)。集合差异＝有 idx 只在一侧出现。"""
    missing = sorted(set(a) ^ set(b))
    worst, worst_at = 0.0, None
    for k in set(a) & set(b):
        d = max(abs(x - y) for x, y in zip(a[k], b[k]))
        if d > worst:
            worst, worst_at = d, k
    return worst, ([f"idx{k}" for k in missing[:5]] if missing else []), not missing


def scroll_through(page) -> None:
    page.evaluate("() => window.scrollTo(0, 0)")
    height = page.evaluate("() => document.documentElement.scrollHeight")
    step = max(400, height // 8)
    y = 0
    while y < height:
        y += step
        page.evaluate("(y) => window.scrollTo(0, y)", y)
        page.wait_for_timeout(90)
    page.wait_for_timeout(250)
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(150)


def check_route(browser, base: str, route: str) -> list[tuple[str, bool, str]]:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.add_init_script(CLS_INIT)
    page.goto(base.rstrip("/") + route, wait_until="load")
    page.wait_for_timeout(SETTLE_MS)

    res: list[tuple[str, bool, str]] = []

    ls = read_cls(page)
    if ls.get("error"):
        res.append(("L5", False, f"{route} CLS 观察器未挂载：{ls['error']}"))
    # L1 加载期
    cls_load = float(ls.get("value") or 0.0)
    res.append((f"L1{route}", cls_load <= CLS_BUDGET,
                f"加载期 CLS={cls_load:.5f}（上界 {CLS_BUDGET}；事件 {ls.get('entries')}）"))

    # L5 非空守卫（追踪集）
    total = page.evaluate(TAG_JS)
    s0 = snap(page)
    res.append((f"L5{route}", len(s0) >= MIN_TRACKED,
                f"追踪集 {len(s0)} 元素（下界 {MIN_TRACKED}；main 内共 {total}）"))

    # L3 主题切换几何零位移（真实控件；测 **浅→深** 这一次真实变化）
    # ⚠ 站点主题是**三态循环**（system→light→dark）⇒ 「点两次」并不回到原点（实测踩到：
    #   点两次后停在 dark，随后的 L4 基线就变成拿 dark 与 light 比 ⇒ 误判）。本处改为
    #   **先推进到 light 作基线、再推进到 dark 作对照**，两次快照间只有主题这一维变化。
    try:
        page.click(THEME_BTN, timeout=3000)
        page.wait_for_timeout(650)
        b3 = snap(page)
        page.click(THEME_BTN, timeout=3000)
        page.wait_for_timeout(650)
        a3 = snap(page)
        d3, miss3, ok3 = diff_snaps(b3, a3)
        res.append((f"L3{route}", ok3 and d3 <= RECT_TOL,
                    f"主题 light→dark max|Δ|={d3:.3f}px（容差 {RECT_TOL}）· 追踪集 {len(a3)}"
                    + (f" · 集合差异 {len(miss3)} 处 {miss3}" if not ok3 else "")))
    except Exception as exc:  # noqa: BLE001
        res.append((f"L3{route}", False, f"主题切换未跑成：{exc}"))

    # L4 动效开关几何零位移（真实控件；测 **动效开→关** 这一次真实变化）
    try:
        page.click(MOTION_BTN, timeout=3000)
        page.wait_for_timeout(500)
        b4 = snap(page)
        page.click(MOTION_BTN, timeout=3000)
        page.wait_for_timeout(500)
        a4 = snap(page)
        d4, miss4, ok4 = diff_snaps(b4, a4)
        res.append((f"L4{route}", ok4 and d4 <= RECT_TOL,
                    f"动效 on→off max|Δ|={d4:.3f}px（容差 {RECT_TOL}）· 追踪集 {len(a4)}"
                    + (f" · 集合差异 {len(miss4)} 处 {miss4}" if not ok4 else "")))
    except Exception as exc:  # noqa: BLE001
        res.append((f"L4{route}", False, f"动效开关未跑成：{exc}"))

    # L2 滚动期 CLS 增量
    before = float(read_cls(page).get("value") or 0.0)
    scroll_through(page)
    after = float(read_cls(page).get("value") or 0.0)
    res.append((f"L2{route}", (after - before) <= CLS_BUDGET,
                f"滚动期 CLS 增量={after - before:.5f}（上界 {CLS_BUDGET}；累计 {after:.5f}）"))

    ctx.close()
    return res


# ─────────────────────────────── selftest ───────────────────────────────
# ⚠ 夹具必须带**两个真实语义的控件**（探针用 `aria-label^="配色主题"` / `^="动效"` 定位）
#   —— 否则 L3/L4 会因「找不到控件」而 FAIL，对照臂恒 FAIL、判据失去意义。
_CTL = (
    '<button aria-label="配色主题：浅色。点击切到深色">theme</button>'
    '<button aria-label="动效：跟随系统。点击切到动效开">motion</button>'
)
_CTL_JS = """<script>
var d=document.documentElement;
document.querySelector('[aria-label^="配色主题"]').addEventListener('click',function(){
  d.getAttribute('data-theme')==='dark'?d.removeAttribute('data-theme'):d.setAttribute('data-theme','dark');});
document.querySelector('[aria-label^="动效"]').addEventListener('click',function(){
  d.getAttribute('data-motion')==='off'?d.setAttribute('data-motion','on'):d.setAttribute('data-motion','off');});
</script>"""
_BASE_CSS = ("body{margin:0;font:14px system-ui} main{padding:20px} "
             ".b{height:40px;margin:8px 0;background:#eee}")


def _fixture(extra_css: str, extra_js: str, blocks: int) -> str:
    """__MAIN__ 由调用处替换 ⇒ ⛔ 不用 `%` 两段格式化（易错且难读）。"""
    return (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8"><style>'
        + _BASE_CSS + extra_css
        + "</style></head><body>" + _CTL + "<main>__MAIN__</main>" + extra_js + _CTL_JS
        + "</body></html>"
    )


# 对照臂：无任何位移
GOOD_FIXTURE = _fixture("", "", 30)
# 负向 L1：首帧后插入高块把内容推下去（真·layout shift）
SHIFT_FIXTURE = _fixture(
    "", '<script>setTimeout(function(){var d=document.createElement("div");'
        'd.style.height="300px";d.style.background="#cde";'
        'document.body.insertBefore(d,document.body.firstChild);},250);</script>', 30)
# 负向 L3：主题切换真的改几何（深色下块变高）
TOGGLE_SHIFT_FIXTURE = _fixture('[data-theme="dark"] .b{height:90px}', "", 30)
# 负向 L5：追踪集过少
TINY_FIXTURE = _fixture("", "", 3)


def _blocks(n: int) -> str:
    return "".join(f'<div class="b">block {i}</div>' for i in range(n))


def _serve(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_port}"


def selftest() -> bool:
    print("== 布局稳定性探针自检（合成夹具；⛔ 不读站点 out/、⛔ 不改仓库）==")
    ok = True
    with TemporaryDirectory() as td:
        root = Path(td)

        def write_fixture(name: str, html: str) -> None:
            d = root / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(html, encoding="utf-8")

        write_fixture("ok", GOOD_FIXTURE.replace("__MAIN__", _blocks(30)))
        write_fixture("shift", SHIFT_FIXTURE.replace("__MAIN__", _blocks(30)))
        write_fixture("tshift", TOGGLE_SHIFT_FIXTURE.replace("__MAIN__", _blocks(30)))
        write_fixture("tiny", TINY_FIXTURE.replace("__MAIN__", _blocks(3)))

        httpd, base = _serve(root)
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()

                def run(route: str) -> dict:
                    # ⚠ 夹具路由只跑 1 条（探针的 ROUTES 是站点路由，此处直接单点调用）
                    return {cid: (passed, detail) for cid, passed, detail in
                            check_route(b, base, route)}

                good = run("/ok/")
                allp = all(ps for ps, _ in good.values())
                ok &= allp
                print(f"  [{'PASS' if allp else 'FAIL'}] 对照臂：稳定夹具全 PASS"
                      + ("" if allp else f" · {[ (k,v) for k,v in good.items() if not v[0] ]}"))

                sh = run("/shift/")
                hit = [k for k, (ps, _) in sh.items() if k.startswith("L1") and not ps]
                ok &= bool(hit)
                print(f"  [{'PASS' if hit else 'FAIL'}] 负向夹具 L1：加载期真·位移被抓到 :: "
                      + str(sh.get("L1/shift/")))

                ts = run("/tshift/")
                hit3 = [k for k, (ps, _) in ts.items() if k.startswith("L3") and not ps]
                ok &= bool(hit3)
                print(f"  [{'PASS' if hit3 else 'FAIL'}] 负向夹具 L3：主题切换改尺寸被抓到 :: "
                      + str(ts.get("L3/tshift/")))

                ti = run("/tiny/")
                hit5 = [k for k, (ps, _) in ti.items() if k.startswith("L5") and not ps]
                ok &= bool(hit5)
                print(f"  [{'PASS' if hit5 else 'FAIL'}] 负向夹具 L5：追踪集过少被抓到 :: "
                      + str(ti.get("L5/tiny/")))
                b.close()
        finally:
            httpd.shutdown()

    print(f"\nSELFTEST: {'ALL PASS' if ok else 'HAS FAILURE'}"
          "（L1/L3/L5 各有能触发它的负向样本 ＋ 1 条对照臂）")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="布局稳定性探针（CLS ＋ 交互期几何零位移）")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--out", default=None, help="留档目录（写 JSON ＋ MD）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    results: list[tuple[str, bool, str]] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for route in ROUTES:
            try:
                results.extend(check_route(b, args.base, route))
            except Exception as exc:  # noqa: BLE001
                results.append((f"L0{route}", False, f"路由未跑成：{exc}"))
        b.close()

    print(f"== 布局稳定性探针（base={args.base}；{len(ROUTES)} 路由）==")
    for cid, passed, detail in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {cid}  {detail}")
    ok = all(ps for _, ps, _ in results)
    print(f"\nLAYOUT-STABILITY: {'ALL PASS' if ok else 'HAS FAILURE'}"
          f"（{sum(1 for _, ps, _ in results if ps)}/{len(results)}）")

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "layout-stability-report.json").write_text(
            json.dumps({"base": args.base, "routes": ROUTES,
                        "cls_budget": CLS_BUDGET, "rect_tol": RECT_TOL,
                        "results": [{"id": c, "pass": ps, "detail": d} for c, ps, d in results]},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [f"# 布局稳定性探针报告（{args.base}）", "",
                 f"- 路由（{len(ROUTES)}）：{' '.join(ROUTES)}",
                 f"- CLS 上界 {CLS_BUDGET}（Core Web Vitals good）· 几何容差 {RECT_TOL}px", "",
                 "| id | 结果 | 读数 |", "|---|---|---|"]
        lines += [f"| {c} | {'PASS' if ps else 'FAIL'} | {d} |" for c, ps, d in results]
        (out / "layout-stability-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[written] {out}/layout-stability-report.json + .md")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
