#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""**行为口径**「反馈面 ≡ 热区」覆盖率取样（只读 out/，不改仓库）。

# ─────────────────────────────────────────────────────────────────────────────
# 来源登记（Provenance）：本件是 scripts/probes/ 下的 **CI 活件**（可演进）。
#   · 归档冻结件：Mission-file/2026-10/1008-个人主页深化改革/batch8-evidence/audit_surface_hit.py
#                  @ 1a06be5 · sha256=addfaf08b036608a77edfb93bc576327b50ee180764c974e150cc71abfefe33b
#   · 漂移方向：本件可演进；归档件⛔ 不追改、不自动同步（保其批报告的逐字节可复现）。
#   · 登记表：scripts/probes/PROVENANCE.json（机检 scripts/probes/check_provenance.py）
#   · 相对归档件的改动（第八批 §4-② 硬化）：BASE 改 --base／SITE_BASE 参数化；argparse 加 --base。
#     ⛔ 判据（阈值 0.98、逃亡门守卫、SKIPPED 语义、取样网格）一字未改。
# ─────────────────────────────────────────────────────────────────────────────

为什么要有这一台（而不是直接用批七的 `audit_site.py`）——
批七的 coverage 是**几何**口径：`hot_area = 该元素自身(若可交互) ＋ 其内部 a/button 的
**几何盒**面积并集`。它对本批引入的新机制**结构性失明**：

    第八批把热区从 `<a>` 的盒子**扩到了整卡**（stretched link：`a::after{inset:0}`），
    而伪元素的命中区**不在 `<a>` 的 bounding rect 里** ⇒ 几何口径读回的还是老数字
    （`.card` 0.131 / `.related__item` 0.194），与真实可点性相反。

这与批七「几何『占用』≠ 显著性『占用』」（D4/踩坑 54）是**同型**的：量错了事实。
⇒ 本仪器改量为「**可点性**」这个事实本身：在反馈面内**布点取样**，
  逐点 `document.elementFromPoint()` 取真实命中元素，再看它能否上溯到
  **位于该反馈面之内**的可交互祖先。命中率即 `hit_coverage`。

    伪元素命中会归因给它的**宿主元素**（`elementFromPoint` 返回 `<a>`）⇒
    stretched link 因此可被正确计入 —— 这是本仪器能看见新机制的关键。

判据（与 `scripts/interaction-surfaces.json` 的 kind 分类口径一致）：
    kind=self       元素自身即交互目标            ⇒ hit_coverage 应 ≥ 0.98
    kind=descendant 某交互目标的后代装饰件        ⇒ 不适用（判据上溯最近交互祖先）
    kind=container  非交互容器                    ⇒ hit_coverage 应 ≥ 0.98
    ★ 批十三新增 kind=decor 装饰性反射面（指针跟随高光）：
        ⇒ 覆盖率**不适用**（装饰层不暗示可点击，无「反馈面 > 热区」的假可供性问题）
        ⇒ 换两条**替代判据**：
            D1 `cursor` 不得为 `pointer`（装饰面 ⛔ 不得用光标暗示可点击）；
            D2 面内（或元素自身）**含交互目标** ⇒ **回退**按 self/container 口径判覆盖率
               （⛔ 防「用 decor 盖章逃过覆盖率」；这条保证 `.card` 这类件的严格度不降）。
        ⚠ 依据＝用户裁决 2026-10-10（V1「所有带边框/圆角容器统一加指针特效」与本站
          「悬停反馈面 ≡ 点击热区」判据**互锁** ⇒ 裁决走「新增 kind ＋ 更严替代判据」）。
          ⛔ 这不是本仪器单方面的放宽：`surface_hit_probe` 与 `gate_interaction_surface.py`
          同批改，且两边都带 `--selftest` 负向夹具。

⚠ 取样面：11×11 网格；跳出该元素子树的点（卡片间空隙、越界）**不计入**分母，如实报出。

用法：
    setsid python3 -m http.server 4399 --directory out >/tmp/…log 2>&1 </dev/null & disown
    python3 scripts/probes/surface_hit_probe.py --out <留档目录>
    python3 scripts/probes/surface_hit_probe.py --out <留档目录> --selftest   # 合成夹具，验证判据非恒真
    SITE_BASE=http://127.0.0.1:4400 python3 scripts/probes/surface_hit_probe.py --out <留档目录>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_BASE = "http://127.0.0.1:4399"
VIEWPORT = {"width": 1440, "height": 900}
NARROW = {"width": 390, "height": 844}
GRID = 11  # 11×11 = 121 个取样点

# ★ 按「同类项全集」取路由（⛔ 只看首页会漏掉 chip/contact/nav 三处反馈面）：
#   `.chip` 只在 /works、`.contact__link` 只在 /about、`.nav__link` 只在窄屏（≤1179px 顶栏接管）。
RUNS: list[tuple[str, str, dict]] = [
    ("/", "light", VIEWPORT),
    ("/", "dark", VIEWPORT),
    ("/works/", "light", VIEWPORT),
    ("/works/", "dark", VIEWPORT),
    ("/works/12-factor-methodology-kg/", "light", VIEWPORT),
    ("/works/12-factor-methodology-kg/", "dark", VIEWPORT),
    ("/about/", "light", VIEWPORT),
    ("/about/", "dark", VIEWPORT),
    ("/", "light", NARROW),
]

INTERACTIVE = 'a, button, [role="button"], summary, input, select, textarea'

ROOT = Path(__file__).resolve().parents[2]
SURFACES_PATH = ROOT / "scripts/interaction-surfaces.json"


def declared_kinds(path: Path = SURFACES_PATH) -> dict[str, str]:
    """登记表（单一真相源）的 selector → kind 映射。

    ⛔ 映射**缺失**时不放行 decor：未登记的 selector 一律按 DOM 推断的 self/container 判覆盖率
    ⇒ decor 豁免**只能**由「登记在案」获得，不构成逃生门。
    """
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {e["selector"]: e.get("kind", "") for e in table.get("entries", [])}


def apply_declared_kind(rows: list[dict], declared: dict[str, str]) -> list[dict]:
    """把登记表声明的 `decor` 落到**每条实例**上（D2 回退就在此处实现）。

    D2：面内（或元素自身）含交互目标 ⇒ 回退按 self/container 口径判覆盖率。
        ⛔ 这条是「decor 不得成为逃生门」的机检保证 —— 它让统一选择器
        `[data-spotlight]` 下 `.card`（可点）与 `.figure`（不可点）分开判，
        前者仍按 ≥0.98 判，不被后者的 0 覆盖污染。
    """
    for row in rows:
        if declared.get(row["selector"]) != "decor":
            continue
        if row["kind"] == "descendant":
            continue                      # 后代装饰件：判据上溯交互祖先，与 decor 无关
        row["declared"] = "decor"
        if row["selfInteractive"]:
            row["kind"] = "self"          # D2：(a) 自身即可交互
        elif row["hasInteractiveInside"]:
            row["kind"] = "container"     # D2：(b) 面内含交互目标
        else:
            row["kind"] = "decor"         # 纯装饰 ⇒ 豁免覆盖率，改判 D1
    return rows

# ---------------------------------------------------------------- 1) 枚举反馈面

ENUM_JS = r"""
() => {
  const hoverSelectors = new Set();
  const walk = (rules) => {
    for (const r of rules) {
      if (r.cssRules && r.cssRules.length) { try { walk(r.cssRules); } catch (e) {} continue; }
      const sel = r.selectorText;
      if (sel && /:hover|:focus-within/.test(sel)) hoverSelectors.add(sel);
    }
  };
  for (const sheet of document.styleSheets) { try { walk(sheet.cssRules); } catch (e) {} }

  // 去伪类 → 产物里的探测选择器（同一复合对象会因多条规则重复出现 ⇒ 按 key 去重）
  const probes = [];
  for (const sel of hoverSelectors) {
    for (const part of sel.split(',')) {
      const p = part.trim();
      const stripped = p.replace(/::?[a-z-]+(\([^)]*\))?/g, ' ').trim();
      if (!stripped) continue;
      probes.push({ original: p, probe: stripped });
    }
  }

  const docs = [];
  // ★ 元素引用表（不用 data-* 属性）：同一元素会被多条选择器命中，
  //   用属性做索引会被后一次覆盖 ⇒ 「element gone」（第一版实测踩到）。
  //   同一元素只注册一次（uid 复用）；(selector, uid) 去重 ⇒ 每条选择器**每个实例**各测一次。
  let uid = 0;
  const registry = (window.__b8 = []);
  const idOf = (el) => {
    if (el.__b8u === undefined) { el.__b8u = uid++; registry[el.__b8u] = el; }
    return el.__b8u;
  };
  const seen = new Set();
  for (const { original, probe } of probes) {
    let nodes;
    try { nodes = document.querySelectorAll(probe); } catch (e) { continue; }
    for (const el of nodes) {
      const b = el.getBoundingClientRect();
      if (b.width < 1 || b.height < 1) continue;
      const st = getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden') continue;
      const id = idOf(el);
      const key = original + '|' + id;
      if (seen.has(key)) continue;
      seen.add(key);

      const isInteractive = el.matches('a, button, [role="button"], summary, input, select, textarea');
      let kind = 'container';
      if (isInteractive) kind = 'self';
      else if (el.closest('a, button, [role="button"], summary')) kind = 'descendant';

      docs.push({
        id, selector: original, probe, kind,
        tag: el.tagName.toLowerCase(),
        cls: (typeof el.className === 'string' ? el.className : ''),
        boxArea: Math.round(b.width * b.height),
        // ★ 批十三：装饰面（decor）判据 D1/D2 的输入（样式已在上面取过）
        cursor: st.cursor,
        selfInteractive: isInteractive,
        hasInteractiveInside: isInteractive
          || !!el.querySelector('a, button, [role="button"], summary, input, select, textarea'),
      });
    }
  }

  // 反向：真实可点目标是否「自身」有 hover 反馈（与批七同口径：探测选择器能否命中它自己）
  const allTargets = [...document.querySelectorAll('a, button, summary')].filter((t) => {
    const b = t.getBoundingClientRect();
    return b.width > 1 && b.height > 1;
  });
  const targets = allTargets.map((t) => {
    let selfHover = false;
    for (const { probe } of probes) { try { if (t.matches(probe)) { selfHover = true; break; } } catch (e) {} }
    return {
      tag: t.tagName.toLowerCase(),
      cls: (typeof t.className === 'string' ? t.className : ''),
      text: (t.textContent || '').trim().slice(0, 24),
      href: t.getAttribute('href') || '',
      coveredByContainer: (() => {
        const li = t.closest('.card, .related__item');
        return li ? li.className : '';
      })(),
      selfHover,
    };
  });

  return { hoverSelectorCount: hoverSelectors.size, rows: docs, targets };
}
"""

# ---------------------------------------------------------------- 2) 布点取样

SAMPLE_JS = r"""
([id, grid]) => new Promise((resolve) => {
  const el = (window.__b8 || [])[id];
  if (!el) { resolve({error: 'element gone'}); return; }

  const sampleOnce = () => {
    const r = el.getBoundingClientRect();
    let considered = 0, hot = 0;
    const misses = [];
    for (let i = 0; i < grid; i++) {
      for (let j = 0; j < grid; j++) {
        const x = r.left + (r.width * (i + 0.5)) / grid;
        const y = r.top + (r.height * (j + 0.5)) / grid;
        if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue;
        const hit = document.elementFromPoint(x, y);
        if (!hit) continue;
        // 命中点跳出该反馈面的子树 ⇒ 不属于本面（间隙/遮挡），不计入分母
        if (hit !== el && !el.contains(hit)) continue;
        considered++;
        const inter = hit.closest('a, button, [role="button"], summary, input, select, textarea');
        if (inter && (inter === el || el.contains(inter))) hot++;
        else if (misses.length < 3) misses.push({ x: Math.round(x), y: Math.round(y),
                                                  tag: hit.tagName, cls: String(hit.className || '').slice(0, 30) });
      }
    }
    return { considered, hot,
             coverage: considered ? +(hot / considered).toFixed(3) : null,
             box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
             misses };
  };

  // ⛔ 不用 Playwright 的 locator 动作（可操作性等待 + hydration 竞态）；
  //    在**同一次** JS 里先滚动、等两帧、再布点，量到的就是真实布局。
  el.scrollIntoView({ block: 'center', behavior: 'instant' });
  requestAnimationFrame(() => requestAnimationFrame(() => {
    let res = sampleOnce();
    // ★ 通用兜底：**焦点揭示型控件**（静止态在视口外，如 `.skip-link{top:-100%}`，聚焦后才显形）
    //   ⇒ 首轮 0 个有效点时不直接判「不可量测」，先聚焦再量一次。
    if (res.considered === 0) {
      try { el.focus({ preventScroll: false }); } catch (e) {}
      requestAnimationFrame(() => requestAnimationFrame(() => {
        const again = sampleOnce();
        resolve({ ...again, revealedByFocus: again.considered > 0 });
      }));
      return;
    }
    resolve(res);
  }));
})
"""


def resolve_base(cli_base: str | None) -> str:
    return cli_base or os.environ.get("SITE_BASE") or DEFAULT_BASE


def measure(page, declared: dict[str, str] | None = None) -> dict:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)  # 让 hydration 落定，避免枚举后被 React 替换掉元素
    audit = page.evaluate(ENUM_JS)
    cache: dict[int, dict] = {}          # 同一元素只取一次样（多条选择器会引用它）
    rows = []
    for row in audit["rows"]:
        if row["id"] not in cache:
            cache[row["id"]] = page.evaluate(SAMPLE_JS, [row["id"], GRID])
        rows.append({**row, **cache[row["id"]]})
    # ★ 批十三：登记表声明的 decor ⇒ 逐实例落到 kind 上（D2 回退）
    rows = apply_declared_kind(rows, declared or {})
    return {"hoverSelectorCount": audit["hoverSelectorCount"], "rows": rows, "targets": audit["targets"]}


def aggregate(rows: list[dict]) -> list[dict]:
    """按 (selector, kind) 聚合：同类项**全集**取样后取最坏覆盖率（⛔ 不用单实例代表全类）。"""
    groups: dict[tuple, dict] = {}
    for row in rows:
        g = groups.setdefault(
            (row["selector"], row["kind"]),
            {"selector": row["selector"], "kind": row["kind"], "instances": 0,
             "coverages": [], "hot": 0, "considered": 0, "worst": None,
             "pointer_cursor": 0},
        )
        g["instances"] += 1
        g["hot"] += row.get("hot") or 0
        g["considered"] += row.get("considered") or 0
        # ★ 批十三 D1 的输入：装饰面的实例里有没有「cursor=pointer」
        if row.get("cursor") == "pointer":
            g["pointer_cursor"] += 1
        if row.get("error") or row.get("coverage") is None:
            continue
        g["coverages"].append(row["coverage"])
        if g["worst"] is None or row["coverage"] < g["worst"]["coverage"]:
            g["worst"] = row
    for g in groups.values():
        g["min_coverage"] = min(g["coverages"]) if g["coverages"] else None
    return sorted(groups.values(),
                  key=lambda g: (g["min_coverage"] if g["min_coverage"] is not None else 9))


def verdict(row: dict) -> str:
    if row["kind"] == "descendant":
        return "不适用（后代装饰件）"
    if row["kind"] == "decor":
        # ★ 批十三：装饰面豁免覆盖率判据，改判 D1（cursor 语义）
        return "装饰面·豁免覆盖率" + ("｜⛔D1 cursor=pointer" if row.get("pointer_cursor") else "")
    c = row.get("min_coverage", row.get("coverage"))
    if c is None:
        return "SKIPPED（不可量测：静止态不进视口，聚焦后亦无有效点）"
    return "一致" if c >= 0.98 else "错位（含死区）"


def failures(agg: list[dict], run_failures_guard: bool = True) -> list[str]:
    """⛔ 空集**不判 FAIL**（不可量测 ≠ 缺陷；哑火恒 FAIL 与恒真是对称失效）。
    但必须防它变成万能逃生门 ⇒ 另设「整轮无一可量测项」守卫，见 main()。"""
    bad = []
    for g in agg:
        if g["kind"] == "descendant":
            continue
        if g["kind"] == "decor":
            # ★ 批十三 D1：装饰性反射面 ⛔ 不得用 `cursor: pointer` 暗示可点击。
            #   （覆盖率对它不适用；但豁免**不等于**免检 —— 见 D2 已把「含交互目标者」
            #    回退成 self/container，故此处只剩纯装饰实例。）
            if g.get("pointer_cursor"):
                bad.append(f'{g["selector"]} → decor/D1：cursor=pointer'
                           f'（{g["pointer_cursor"]}/{g["instances"]} 实例；装饰面不得暗示可点击）')
            continue
        c = g["min_coverage"]
        if c is None:
            continue
        if c < 0.98:
            bad.append(f'{g["selector"]} → {g["kind"]}/min_coverage={c}（{g["instances"]} 实例）')
    return bad


def measurable_count(agg: list[dict]) -> int:
    return sum(1 for g in agg if g["kind"] != "descendant" and g["min_coverage"] is not None)


# ---------------------------------------------------------------- selftest

SELFTEST_SETUP = r"""
() => {
  const style = document.createElement('style');
  style.textContent = `
    .st-container:hover { outline: 1px solid red; }
    .st-stretched:hover { outline: 1px solid red; }
    /* ⛔ 夹具本身就踩过 Bootstrap 那个坑：给链接加 position:relative ⇒ 拉伸层缩回链接盒。
       正解＝链接保持 static，containing block 落回有定位的祖先（这里是 div）。 */
    .st-stretched a { display: block; width: 60px; height: 20px; }
    .st-stretched a::after { content: ''; position: absolute; inset: 0; z-index: 1; }
    .st-self:hover { color: red; }
    .st-link:hover svg { opacity: 1; }
    /* ★ 批十三 decor 夹具 */
    .st-decor:hover { outline: 1px solid red; }
    .st-decor-bad:hover { outline: 1px solid red; }
    .st-decor-hot:hover { outline: 1px solid red; }
    .st-decor-hot a { display: block; width: 60px; height: 20px; }
    .st-decor-hot a::after { content: ''; position: absolute; inset: 0; z-index: 1; }
  `;
  document.head.appendChild(style);

  const mk = (cls, w, h, top) => {
    const d = document.createElement('div');
    d.className = cls;
    d.style.cssText = `position:fixed;left:0;top:${top}px;width:${w}px;height:${h}px;background:#eee;z-index:9999;`;
    document.body.appendChild(d);
    return d;
  };

  // 1) 非交互容器 200x100，内含唯一的 40x20 链接 ⇒ 真命中率 ≈ 0.04（应判错位）
  const c = mk('st-container', 200, 100, 0);
  const l1 = document.createElement('a');
  l1.className = 'st-link'; l1.href = '#st';
  l1.style.cssText = 'display:block;width:40px;height:20px;background:#333;';
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '10'); svg.setAttribute('height', '10');
  l1.appendChild(svg); c.appendChild(l1);

  // 2) 同样的容器，但链接带 stretched ::after 铺满整块 ⇒ 真命中率 ≈ 1（应判一致）
  //    ★ 关键：几何口径读不出来（仍 ≈0.04），行为口径才能看见 —— 这就是本仪器的存在理由
  const s = mk('st-stretched', 200, 100, 120);
  const l2 = document.createElement('a');
  l2.href = '#st2'; l2.textContent = 'x';
  s.appendChild(l2);

  // 3) 自身即交互 → 应判一致
  const a3 = document.createElement('a');
  a3.className = 'st-self'; a3.href = '#st3'; a3.textContent = 'self';
  a3.style.cssText = 'position:fixed;left:0;top:230px;width:100px;height:30px;z-index:9999;background:#333;';
  document.body.appendChild(a3);

  // ★ 批十三 decor 三夹具（配合 SELFTEST_DECLARED 把这三条声明为 decor）
  //   5) 纯装饰：无可交互目标、cursor 默认 ⇒ 应判 decor 且 D1 通过
  const d5 = mk('st-decor', 200, 100, 280);
  d5.textContent = 'decor';
  //   6) 装饰 + cursor:pointer ⇒ 应判 decor 但 **D1 违规**
  const d6 = mk('st-decor-bad', 200, 100, 400);
  d6.style.cursor = 'pointer';
  d6.textContent = 'decor-bad';
  //   7) 声明为 decor，但面内含 stretched 链接 ⇒ **D2 回退**按 container 口径判覆盖率
  const d7 = mk('st-decor-hot', 200, 100, 520);
  const l7 = document.createElement('a');
  l7.href = '#st7'; l7.textContent = 'x';
  d7.appendChild(l7);
}
"""

# ★ 批十三：夹具用的「声明表」替身（模拟 interaction-surfaces.json 的 kind 声明）
SELFTEST_DECLARED: dict[str, str] = {
    ".st-decor:hover": "decor",
    ".st-decor-bad:hover": "decor",
    ".st-decor-hot:hover": "decor",
}


def selftest(page) -> list[dict]:
    page.evaluate(SELFTEST_SETUP)
    page.wait_for_timeout(200)
    measured = measure(page, SELFTEST_DECLARED)
    by_sel: dict[str, dict] = {}
    for row in measured["rows"]:
        by_sel.setdefault(row["selector"], row)
    checks = []

    def add(case, expect_ok, row, detail):
        checks.append({"case": case, "expected": detail, "got": (verdict(row) if row else "MISSING"),
                       "ok": bool(row) and expect_ok})

    r1 = by_sel.get(".st-container:hover")
    add("负向夹具：非交互容器 200x100 内仅 40x20 链接", r1 and r1["coverage"] is not None and r1["coverage"] < 0.98,
        r1, "应判错位（coverage 显著 < 0.98）")

    r2 = by_sel.get(".st-stretched:hover")
    add("对照臂：同容器 + stretched ::after 铺满整块", r2 and (r2["coverage"] or 0) >= 0.98,
        r2, "应判一致（coverage ≥ 0.98，几何口径看不见的机制）")

    r3 = by_sel.get(".st-self:hover")
    add("对照臂：元素自身即交互目标", r3 and (r3["coverage"] or 0) >= 0.98, r3, "应判一致")

    r4 = by_sel.get(".st-link:hover svg")
    add("对照臂：链接内部的后代装饰件", r4 and r4["kind"] == "descendant", r4, "应判不适用（descendant）")

    # ★ 批十三 decor 判据（D1/D2）的负向与对照夹具
    r5 = by_sel.get(".st-decor:hover")
    add("★批十三 对照臂：纯装饰面（无可交互目标，cursor 默认）",
        r5 and r5["kind"] == "decor" and r5.get("cursor") != "pointer", r5,
        "应判 decor、豁免覆盖率、D1 通过")

    r6 = by_sel.get(".st-decor-bad:hover")
    add("★批十三 负向夹具：装饰面 cursor:pointer",
        r6 and r6["kind"] == "decor" and r6.get("cursor") == "pointer", r6,
        "应判 decor **且** D1 违规（装饰面不得暗示可点击）")

    r7 = by_sel.get(".st-decor-hot:hover")
    add("★批十三 负向夹具：声明 decor 但面内含可交互目标",
        r7 and r7["kind"] == "container", r7,
        "应 D2 回退成 container（⛔ 防用 decor 盖章逃过覆盖率）")
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description="行为口径的反馈面≡热区覆盖率取样")
    ap.add_argument("--out", required=True, type=Path, help="报告落盘目录（⛔ 不写仓库）")
    ap.add_argument("--base", default=None,
                    help=f"站点基址（缺省 {DEFAULT_BASE}；亦可由 SITE_BASE 环境变量给出）")
    ap.add_argument("--selftest", action="store_true", help="注入合成夹具验证判据非恒真（不写主报告）")
    args = ap.parse_args()
    base = resolve_base(args.base)
    args.out.mkdir(parents=True, exist_ok=True)
    # ★ 批十三：登记表是 decor 声明的**单一真相源**。缺表 ⇒ declared={} ⇒ 无 decor 豁免。
    declared = declared_kinds()
    if declared:
        n_decor = sum(1 for k in declared.values() if k == "decor")
        print(f"[登记表] {SURFACES_PATH.name}：{len(declared)} 条选择器，其中 decor {n_decor} 条")
    else:
        print(f"[登记表] ⚠ 未读到 {SURFACES_PATH} ⇒ 本次**无 decor 豁免**（一律按覆盖率判）")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        if args.selftest:
            page = browser.new_page(viewport=VIEWPORT)
            page.goto(base + "/", wait_until="networkidle")
            checks = selftest(page)
            page.close()
            browser.close()
            print("== selftest（合成夹具；⛔ 不写主报告）==")
            for c in checks:
                print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['case']}｜期望 {c['expected']}｜实得 {c['got']}")
            ok = all(c["ok"] for c in checks)
            print("  SELFTEST:", "PASS" if ok else "FAIL（判据可能恒真）")
            return 0 if ok else 1

        report: dict = {"base": base, "grid": GRID, "runs": []}
        for path, theme, viewport in RUNS:
            page = browser.new_page(viewport=viewport)
            page.goto(base + path, wait_until="networkidle")
            page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
            page.wait_for_timeout(250)
            measured = measure(page, declared)
            page.close()
            agg = aggregate(measured["rows"])
            label = f"{path} · {theme} · {viewport['width']}px"
            report["runs"].append({"path": path, "theme": theme, "width": viewport["width"],
                                   "hoverSelectorCount": measured["hoverSelectorCount"],
                                   "instances": len(measured["rows"]),
                                   "aggregated": agg, "targets": measured["targets"]})
            print(f"== {label} ==")
            print(f"   反馈规则 {measured['hoverSelectorCount']} 条 · 反馈面实例 {len(measured['rows'])} 个 "
                  f"· 同类聚合 {len(agg)} 类")
            for g in agg:
                print(f"   [{verdict(g):18s}] {g['selector']:44s} {g['kind']:10s} "
                      f"实例 {g['instances']:2d} · 最坏覆盖 {g['min_coverage']} · 合计 {g['hot']}/{g['considered']}")
            bad = [t for t in measured["targets"] if not t["selfHover"]]
            print(f"   反向（自身无 hover 反馈）：{len(bad)} 个")
            for t in bad:
                print(f"     - {t['tag']}.{t['cls'] or '-'} 「{t['text']}」")

        browser.close()

    # ⛔ 不可对「已聚合行」再聚合（它们的字段是 min_coverage 而非 coverage）。
    bad = []
    skipped: list[str] = []
    for run in report["runs"]:
        tag = f"[{run['path']} · {run['theme']} · {run['width']}px]"
        for item in failures(run["aggregated"]):
            bad.append(f"{tag} {item}")
        for g in run["aggregated"]:
            if g["kind"] != "descendant" and g["min_coverage"] is None:
                skipped.append(f"{tag} {g['selector']}")
        # ★ 逃亡门守卫：若某轮**一个可量测项都没有**，判据在该轮等于哑火 ⇒ FAIL
        if measurable_count(run["aggregated"]) == 0:
            bad.append(f"{tag} 本轮无任何可量测反馈面 —— 判据在此轮哑火（⛔ 不得静默通过）")
    report["skipped_unmeasurable"] = skipped
    report["failures"] = bad
    report["result"] = "ALL PASS" if not bad else f"HAS FAILURE（{len(bad)}）"

    (args.out / "surface-hit-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 行为口径「反馈面 ≡ 热区」取样", "",
             f"- 路由×主题×宽度 {len(report['runs'])} 轮 · 取样网格 {GRID}×{GRID}",
             "- 口径：面内布点 → `elementFromPoint` → 命中元素能否上溯到**位于该面之内**的可交互祖先。",
             "- 每个选择器对**全部实例**取样，取最坏覆盖率（⛔ 不用单实例代表全类）。",
             "- ⚠ 几何口径（批七 `audit_site.py`）对伪元素命中区结构性失明，两口径**不可互换**。", ""]
    for run in report["runs"]:
        lines += [f"## {run['path']} · {run['theme']} · {run['width']}px", "",
                  "| selector | kind | 实例数 | 最坏覆盖率 | 合计命中/取样 | 判定 |", "|---|---|---|---|---|---|"]
        for g in run["aggregated"]:
            lines.append(f"| `{g['selector']}` | {g['kind']} | {g['instances']} | "
                         f"{g['min_coverage']} | {g['hot']}/{g['considered']} | {verdict(g)} |")
        lines.append("")
        bad = [t for t in run["targets"] if not t["selfHover"]]
        lines += [f"反向：自身无 hover 反馈的可点目标 {len(bad)} 个"
                  "（`.skip-link` 属有意：它 `:focus` 才显形，是键盘专用跳转）", ""]
    lines += ["## 结论", "",
              f"`{report['result']}`" + (f"：\n\n" + "\n".join(f"- {b}" for b in bad)
                                          if bad else "：所有 self/container 反馈面最坏 hit 覆盖率 ≥ 0.98"),
              ""]
    lines += ["## SKIPPED（不可量测，⛔ 既不算 PASS 也不算 FAIL）", ""]
    lines += [f"- {s}" for s in report["skipped_unmeasurable"]] or ["- 无"]
    lines += ["", "> 说明：静止态不进入视口的控件（如 `.skip-link{top:-100%}`）聚焦后会重取样一次；",
              "> 若仍无有效点则记 SKIPPED。⛔ 不得把 SKIPPED 读成达标，也不得读成缺陷。", ""]
    (args.out / "surface-hit-report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\nSURFACE HIT: {report['result']}")
    print(f"[written] {args.out/'surface-hit-report.json'} + surface-hit-report.md")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
