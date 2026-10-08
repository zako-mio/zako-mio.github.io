# zako-mio.github.io

技术知识中枢主页（v2）：**作品集（B）＋ 枢纽聚合（E）** 双主线，全量索引 `zako-mio` 名下已启用 GitHub Pages 的公开项目。

- 站点：**Next.js 15**（App Router，`output: 'export'` **纯静态导出** → `out/`）
- 路由（IA-3）：`/` · `/works` · `/works/<name>` · `/stats` · `/about`
- 数据管道：`scripts/`（Python 标准库，分层：sources / domain / cli）
- 自动更新：GitHub Actions 每日 03:17 UTC + 手动触发

## 为什么是静态导出

部署目标是 GitHub Pages（纯静态托管），因此 **任何 SSR / Route Handler / 服务端运行时特性都不得引入**。
`next.config.mjs` 的 `output: 'export'` 是硬约束，不是可调选项。

## 本地开发

```bash
pnpm install
python3 scripts/cli.py --config site.config.json --out src/data/projects.json   # 或 pnpm fetch
pnpm dev            # http://localhost:4321
pnpm build          # next build -> out/
pnpm preview        # 起静态服务器预览 out/
```

> gh token：`export GH_TOKEN=$(gh auth token)`（提升速率上限，避免未认证 60/h 限制）

## 门控（读真实产物，不读源码自述）

```bash
python3 scripts/validate_catalog.py src/data/projects.json src/data/projects.schema.json
python3 scripts/gate_contrast.py          # 对比度：读 src/app/globals.css 的真实令牌
python3 scripts/smoke_static.py           # 静态导出冒烟：读 out/ 的实产物
```

两道脚本都带 `--selftest`（内置**负向夹具**，用来证明判据不是恒真）：

```bash
python3 scripts/gate_contrast.py --selftest
python3 scripts/smoke_static.py --selftest
```

## 设计系统约定

- **角色令牌**（`src/app/globals.css` 的 `:root` / `:root[data-theme='dark']`）与
  `fe-starter-kit/tokens/contract.json` 的 11 个 role 同名对齐：`text.primary` / `text.secondary` /
  `text.tertiary` / `link` / `brand.primary` / `border.line` / `border.subtle` / `surface.page` /
  `surface.raised` / `surface.subtle` / `surface.stripe` ⇒ 便于后续新增 binding 时逐角色映射。
- **明暗三态**：`跟随系统`（无属性）/ `[data-theme='light']` / `[data-theme='dark']`。
  ⛔ **不要改用 `light-dark()`**：栈 B/C 的 CSS 管线会把它降级为静态双变量，运行时改
  `color-scheme` 不会重算（`fe-starter-kit/docs/STACK-NOTES.md` 两栈各复现一次）。
  `color-scheme` 由 CSS 选择器分支承担，`data-theme` 由 pre-paint 内联脚本落定。
- **语义 HTML**：卡片取消整卡覆盖层，交互目标是显式链接（键盘 / 屏幕阅读器友好）。

## 已知取舍

- 静态导出 + 客户端筛选 ⇒ 首屏共享 JS 约 102 KB（React 运行时基线）。相比 v1 的 Astro（零 JS 基线）
  是本次换栈明确接受的成本；换来的是完整 React 生态的交互上限。

## 留档

架构决策（ADR-001）与选型矩阵见 Mission 目录 `1008-个人主页深化改革/`。
