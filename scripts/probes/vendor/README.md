# scripts/probes/vendor/ —— 探针层 vendored 第三方资产

本目录存放**探针层**（非站点本体）依赖的第三方**前端资产**。
⛔ 站点本体（`src/`）不依赖本目录；本目录只被 `scripts/probes/` 下的探针在**测试时**读取。

## `axe.min.js`

| 字段 | 值 |
|---|---|
| 包 | [`axe-core`](https://www.npmjs.com/package/axe-core) |
| 版本 | **4.14.0**（pinned；⛔ 升级须同批复跑 `axe_a11y_probe.py --selftest` 与本体） |
| 许可 | **MPL-2.0**（Deque Systems, Inc.；文件头保留完整版权声明） |
| 来源 | `https://unpkg.com/axe-core@4.14.0/axe.min.js` |
| sha256 | `20c09fe157a8a34a30e241aaa1fcdade657734f08ab379ecfbeb7d45cc46e878` |
| 用途 | `scripts/probes/axe_a11y_probe.py` 注入页面后跑 `axe.run()`（无障碍自动化审查） |

**为什么 vendor 而不是 CI 现拉**：可复现性与离线可用 —— ① CI 拉第三方 CDN 会引入网络抖动
（且 CI 未配代理）；② 版本会随时间漂移 ⇒ 判据不可复现。故 pin 死一份并记 sha256。

**为什么不用 `pnpm add`（Node 侧）**：本站的浏览器层探针栈是 **Python + playwright**
（见 `../requirements-probes.txt`），axe-core 是纯前端 JS，用 `page.add_script_tag()` 注入即可，
⛔ 不必为一个测试资产再引 Node 工具链 / selenium。

⚠ 升级流程：换文件 → 更新本表（版本/sha256）→ 跑 `axe_a11y_probe.py --selftest`（对照臂＋负向臂）
→ 跑 `axe_a11y_probe.py`（本体，须 0 违规）→ 若出现新违规，按其性质**修**或**显式豁免（带理由）**。
