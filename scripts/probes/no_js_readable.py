#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「无 JS 可读」共享判据实现（**单一真相源**，供门控与探针共同调用）。

★ 为什么要抽出来（批十五 W2-②）：此前有**两处各写一份**的风险 ——
  ① `scripts/probes/term_layer_probe.py` 的 `T6`：术语解释层的定义文本是否在**原始 HTML** 里；
  ② `scripts/smoke_static.py` 的 `S6`：每页剥 `script/style` 后的可见文字量。
  ⇒ 纪律：**同一口径只留一份实现**；两处都调本模块（⛔ 不各写一份）。

★ 「无 JS 可读」的本体：**内容必须在服务端渲染进 HTML**，⛔ 不能靠 JS 注入。
  故取证通道**必须绕开浏览器** —— 走浏览器时 JS 早已执行＝**没测**（b15#4）。
  本模块因此只做**纯字符串**判据，⛔ 不 import playwright
  （`smoke_static` 在 CI 里跑在浏览器依赖安装**之前**）。

⚠ 声明的不覆盖面：本模块只判「内容在不在原始 HTML 里」，⛔ 不判内容是否**正确/完整**
   （那属 `gate_metrics` / `reverify` 的数字对账，与「可读通道」是两回事）。
"""
from __future__ import annotations

import re

_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<script.*?</script>", re.S | re.I)
_STYLE = re.compile(r"<style.*?</style>", re.S | re.I)
_WS = re.compile(r"\s+")
_TERM_BODY = re.compile(r'<span class="term__body">(.*?)</span>', re.S)


def strip_markup(html: str) -> str:
    """剥 `script`/`style` 与标签，压空白 ⇒ 返回“无 JS 时读得到的”可见文字。"""
    text = _SCRIPT.sub(" ", html)
    text = _STYLE.sub(" ", text)
    text = _TAG.sub(" ", text)
    return _WS.sub(" ", text).strip()


def visible_chars(html: str) -> int:
    return len(strip_markup(html))


def raw_html_has_definition(html: str, min_len: int = 20) -> bool:
    """原始 HTML 里是否存在**非空**的术语定义文本（`.term__body`，且宿主面板 `.term__def` 也在）。

    ⚠ 判据对象＝**产物真实书写形态**：面板出来是
      `<span class="term__def" …><span class="term__name">…</span><span class="term__body">定义</span>…</span>`
      ⇒ 直接锚 `term__body`（⛔ 不要按「几个连续 `</span>`」猜结尾 —— 第一版就这么写错过）。
    """
    if 'class="term__def"' not in html:
        return False
    return any(len(_TAG.sub("", m.group(1)).strip()) >= min_len for m in _TERM_BODY.finditer(html))


def pages_with_declared_terms(pages: dict[str, str]) -> dict[str, str]:
    """筛出「声明了术语解释层」的页面（含 `class="term__def"`）。"""
    return {name: html for name, html in pages.items() if 'class="term__def"' in html}


def term_panels_no_js_problems(pages: dict[str, str], min_len: int = 20) -> list[str]:
    """**全页**扫描：凡声明了术语面板的页面，其定义文本必须在原始 HTML 中（⛔ 不靠 JS 注入）。

    返回问题清单（空 = 全通过）。这是 `term_layer_probe.T6` 的**单页版**在全站上的推广 ——
      ⛔ 两处共用同一实现，避免口径漂移。
    """
    problems: list[str] = []
    for name, html in sorted(pages_with_declared_terms(pages).items()):
        if not raw_html_has_definition(html, min_len):
            problems.append(f"{name}：声明了 .term__def 但原始 HTML 里没有非空定义文本（⛔ 不可无 JS 读）")
    return problems
