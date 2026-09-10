# zako-mio.github.io

技术知识中枢主页：全量自动索引 `zako-mio` 名下已启用 GitHub Pages 的公开项目。

- 站点：Astro（构建期消费 `src/data/projects.json`）
- 数据管道：`scripts/`（Python 标准库，分层：sources / domain / cli）
- 自动更新：GitHub Actions 每日 03:17 UTC + 手动触发

## 本地开发

```bash
npm ci                 # 安装依赖
python3 scripts/cli.py --config site.config.json --out src/data/projects.json
npm run build          # astro build -> dist/
npm run dev            # 本地预览
```

> gh token：`export GH_TOKEN=$(gh auth token)`（提升速率上限，避免未认证 60/h 限制）

详见 `PHASE3-REV1-最终架构与执行计划.md`（留档于 Mission 目录）。
