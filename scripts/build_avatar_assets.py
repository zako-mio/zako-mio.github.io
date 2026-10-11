#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""头像素材构建脚本（批二十点六 · 首页 Hero 左区个性化头像）。

★ 素材（批二十点六新增）：`assets/avatar/zako-mio-avatar-source.jpg`
  · 原始尺寸 1080×1071，JPEG（基线）。sha256 见 `assets/avatar/SOURCE.sha256`。
  · 来源：用户提供的个性化头像素材（开源形象 ＋ AIGC，非商用、无署名义务；
    用户 2026-10-11 裁决「不具有身份标记作用，主要是个性化展示」）。
  · ⚠ 原图**含 meme 文案**（顶部「这群用户到底有什么用呢？」）⇒ 裁切窗必须把它排除。

★ 裁切参数的由来（⛔ 不是随手取的数，逐条有实测依据）：
  · 取心 `CX=542, CY=520`：脸部水平取心的三种独立口径交叉后取中 ——
    双眼中点 x=539 / 全身肤色均值 x=543 / 目视复核；⛔ 不采信单一口径。
  · 边长 `D=400`：在「圆内插画白底占比」与「边缘带（最外 8% 半径）插画白底占比」
    两指标上扫过 D=380..560 ⇒ D=400 是**保住头饰、又不让白底占满圆周**的拐点
    （实测：D=400 圆内白底 2.4% / 边缘带 12.6%；D=430 为 11.6% / 32.1%）。
    ⚠ D 再小（380）边缘带白底可降到 4.2%，但白色荷叶边头饰被切掉 —— 那是角色的
    识别特征，不划算。
  · ⛔ 文案排除：`CY - D/2 = 320` > 文案底缘约 230 ⇒ 结构性排除，不靠目视。
  · 112px 显示时源倍率 400/112 = **3.57x**（2x retina 富余）。

★ 幂等：同一 Pillow 版本 + 同一参数 ⇒ 产物逐字节一致（可复跑核验）。
  ⛔ 本脚本**不做**：抠图（白色荷叶边与白底相连，抠边会啃掉蕾丝高光）、
  羽化/渐隐（背景是两张不同照片，无同色可依 ⇒ 必露灰边）、调色（篡改素材）。
  这三条的排除理由见 `report-batch20.6.md`。

用法：
  python3 scripts/build_avatar_assets.py            # 写入 public/avatar/
  python3 scripts/build_avatar_assets.py --check    # 只校验产物与现有一致（⛔ 不写）
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "avatar" / "zako-mio-avatar-source.jpg"
OUT_DIR = ROOT / "public" / "avatar"

# ── 裁切几何（唯一真相源；同值被测试/文档引用） ─────────────────────────────
CX = 542
CY = 520
D = 400

# ── 派生尺寸：112（桌面显示）与 224（其 2x）；窄屏复用 112 的 2x 档 ─────────
#   ⛔ 尺寸表只留渲染真正会用到的档：`sizes` 声明 (min-width:1024px) 112px, 84px
#   ⇒ 84@2x=168 < 224 ⇒ 浏览器取 224，故不再单独派生 168。
SIZES = [112, 224]

WEBP_QUALITY = 90
WEBP_METHOD = 6  # 确定性：同参数同 Pillow ⇒ 同字节


def crop_source() -> Image.Image:
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    box = (CX - D // 2, CY - D // 2, CX + D // 2, CY + D // 2)
    if box[0] < 0 or box[1] < 0 or box[2] > w or box[3] > h:
        raise SystemExit(f"裁切窗 {box} 越出源图 {(w, h)}")
    if box[1] <= 230:
        raise SystemExit(f"裁切窗上边界 {box[1]} 未越过 meme 文案底缘（约 230）")
    return im.crop(box)


def build(check_only: bool = False) -> int:
    if not SRC.exists():
        raise SystemExit(f"源件缺失：{SRC}")
    src_sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
    base = crop_source()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    drift: list[str] = []
    for size in SIZES:
        img = base if size == D else base.resize((size, size), Image.LANCZOS)
        out = OUT_DIR / f"avatar-{size}.webp"
        tmp = out.with_suffix(".webp.tmp")
        img.save(tmp, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
        blob = tmp.read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        if check_only:
            tmp.unlink()
            if not out.exists():
                drift.append(f"{out.name}: 缺失")
            elif hashlib.sha256(out.read_bytes()).hexdigest() != sha:
                drift.append(f"{out.name}: 与重建结果不一致")
            else:
                print(f"  [ok] {out.relative_to(ROOT)}  sha256={sha[:16]}…")
        else:
            tmp.replace(out)
            print(f"  [write] {out.relative_to(ROOT)}  {size}×{size}  sha256={sha[:16]}…")

    print(f"源件 sha256={src_sha}")
    print(f"裁切 box=({CX - D // 2},{CY - D // 2},{CX + D // 2},{CY + D // 2}) D={D}")
    if check_only and drift:
        print("AVATAR ASSETS: FAIL —— 产物与重建不一致：")
        for d in drift:
            print(f"  ✗ {d}")
        return 1
    print("AVATAR ASSETS: ALL PASS（幂等可复跑）" if check_only else "AVATAR ASSETS: 已生成")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验产物与重建结果一致，⛔ 不写文件")
    args = ap.parse_args()
    sys.exit(build(check_only=args.check))
