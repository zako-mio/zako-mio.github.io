#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""背景素材构建脚本（第六批 · 用公开素材替换「自绘」背景）。

★ 背景：第五批的背景是**纯 CSS radial-gradient 点阵**，成片模糊、被判定为「自绘」。
  本批改为**真实公开素材**，并从原图机械派生站点所需的多分辨率 WebP。

素材与许可（逐条核验，详见 report-batch6.md §素材）：
  · night = ESO eso0934a《A 340-million pixel starscape from Paranal》（S. Guisard）
      https://cdn.eso.org/images/large/eso0934a.jpg      License: CC BY 4.0（须署名）
  · day   = "Lofoten, Norway (Unsplash)" 极光天幕（裁掉地面景物）
      https://upload.wikimedia.org/wikipedia/commons/8/86/Lofoten%2C_Norway_%28Unsplash%29.jpg
      License: CC0 1.0（无署名义务，允许任意修改）

★ day 为什么不是「原图直接低透明度」：浅色页底近白，直接把夜景照片以低不透明度
  合成上去会把整页压成灰幕（原图暗天空占大半）。⇒ 按**亮度做逐像素 alpha** 派生
  「浅色纱幕」：暗天空 → 纯白（不留灰），极光高亮区 → 保留柔和的真实结构。
  派生公式（纯函数、无时钟）：
      mask  = smoothstep(lum, 0.16, 0.62) ** 1.15      # 只留极光本体
      alpha = 0.62 * mask
      out   = src * alpha + white * (1 - alpha)        # 与白底合成
  产物仍是「真实素材」，只是 tonal 重映射；CC0 允许任意改作。

★ 幂等：同一 Pillow 版本 + 同一参数 ⇒ 产物逐字节一致（可复跑核验）。

用法：
  python3 build_backdrop_assets.py --src <原始素材目录> --out <仓库>/public/backdrop
原始素材不入仓（体积），需自行按上面 URL 下载为 eso0934a.jpg / lofoten_cc0.jpg。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

WHITE = 1.0
NIGHT_WIDTHS = [1280, 1920, 2560]
DAY_WIDTHS = [1280, 1920, 2560]
# 窄屏（竖屏）专用：横向大图被 `cover` 放大后会软，故另出一条**竖版裁切**。
# 裁切窗口按原图 9:16 取宽（高占满），起点选在银河亮部与暗尘埃交界处。
PORTRAIT_W, PORTRAIT_H = 1080, 1920
PORTRAIT_CROP_X = 2400


def _smoothstep(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _resize(im: Image.Image, width: int) -> Image.Image:
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def build_night(src: Path, out: Path) -> list[str]:
    """夜间：ESO 银河原图（真实星空），多分辨率 WebP + 一档竖版裁切。"""
    lines: list[str] = []
    im = Image.open(src).convert("RGB")
    for w in NIGHT_WIDTHS:
        r = _resize(im, w)
        dst = out / f"night-{w}.webp"
        r.save(dst, "WEBP", quality=78, method=6)
        lines.append(f"{dst.name} {r.size[0]}x{r.size[1]} {dst.stat().st_size / 1024:.0f}KB")

    # 竖版：按目标 9:16 从原图取一条（高占满），再缩到 PORTRAIT_* 尺寸
    w0, h0 = im.size
    crop_w = min(w0, round(h0 * PORTRAIT_W / PORTRAIT_H))
    left = max(0, min(w0 - crop_w, PORTRAIT_CROP_X))
    p = im.crop((left, 0, left + crop_w, h0)).resize((PORTRAIT_W, PORTRAIT_H), Image.LANCZOS)
    dst = out / f"night-portrait-{PORTRAIT_W}.webp"
    p.save(dst, "WEBP", quality=78, method=6)
    lines.append(f"{dst.name} {p.size[0]}x{p.size[1]} {dst.stat().st_size / 1024:.0f}KB")
    return lines


def build_day(src: Path, out: Path) -> list[str]:
    """日间：极光天幕 → 逐像素 alpha 派生的浅色纱幕（暗天空归白，不产生灰幕）。"""
    lines: list[str] = []
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im = im.crop((0, 0, w, int(h * 0.62)))  # 去掉地面景物，只留天幕
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    mask = _smoothstep(lum, 0.16, 0.62) ** 1.15
    alpha = (0.62 * mask)[..., None]
    out_arr = a * alpha + WHITE * (1.0 - alpha)
    veil = Image.fromarray((np.clip(out_arr, 0.0, 1.0) * 255.0).astype(np.uint8))
    for w2 in DAY_WIDTHS:
        r = _resize(veil, w2)
        dst = out / f"day-{w2}.webp"
        r.save(dst, "WEBP", quality=82, method=6)
        lines.append(f"{dst.name} {r.size[0]}x{r.size[1]} {dst.stat().st_size / 1024:.0f}KB")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="原始素材目录（含 eso0934a.jpg / lofoten_cc0.jpg）")
    ap.add_argument("--out", required=True, help="输出目录（仓库 public/backdrop）")
    args = ap.parse_args()
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in (("eso0934a.jpg", build_night), ("lofoten_cc0.jpg", build_day)):
        p = src / name
        if not p.exists():
            raise SystemExit(f"缺少源素材：{p}")
        for line in fn(p, out):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
