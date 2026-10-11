#!/usr/bin/env node
/**
 * E 指标图表生成（2b-4）· 构建期 Node SSR → SVG。
 *
 * 能力层取用：`echarts-declarative-chart-svg`
 * （记录见 ~/.config/opencode/lib/frontend-capability/records/<key>.json；调用协议见 call.md）
 * ★ 批二十点五（F3 裁决＝单色）：**退役** `d3-scale-chromatic-schemes` 取用 ——
 *   原色板按**行序**取色（`palette[index % len]`）＝彩虹条形图，色相**不承载信息**，
 *   却把「单测度排序数据」视觉上诱导成「分类」，与图件 note 的「不解读为复杂度排序」相抵。
 *   现全部柱用**站点品牌令牌** `--brand-primary`（同一份 globals.css 解析，fail-closed）。
 *   ⚠ **跨线通告**：这改变了前端能力线「d3-scale-chromatic-schemes 已被真实消费」的状态读数，
 *   该记录在 `~/.config/opencode/lib/frontend-capability/records/`（**本仓 ⛔ 不改他线资产**），
 *   通告随 `Mission-file/2026-10/1008-个人主页深化改革/report-batch20.5.md` 登记。
 *
 * ★ 严格遵循记录 usage.requires_config 的四条硬约束（省略任一条都会失败或失真）：
 *   1. 必须 `init(null, null, {renderer:'svg', ssr:true, width, height})`；
 *      省略 `ssr:true` 会抛 `TypeError: Cannot read properties of null (reading 'getAttribute')`
 *   2. 必须显式 `chart.dispose()`；省略时子进程跑完**不退出**（挂起而非报错）
 *   3. 确定性：`animation:false` ＋ 不含随机布局（本图用 bar，无 force 布局）
 *   4. 逐字节基准须**跨进程**比对（同进程二次渲染 class 前缀递增 zr0→zr1）
 *
 * ★ E1/E3 口径约束：图表只放「同类 scope」的比较；⛔ 不跨区并比。
 *   本图 = DAG 图谱区内各项目**主入口图**的实体数（主 scope := 该项目 figures[0]）。
 *   不同项目对「实体」的用词不同（包/插件节点/知识点…），故图内标注口径出处。
 *
 * ★ 派生纪律：产物**不含运行时钟**（禁 generated_at），只带上游事实 as_of ⇒ 幂等可复现。
 *
 * 用法：node scripts/build_charts.mjs [--metrics ...] [--catalog ...] [--out ...]
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

import * as echarts from 'echarts';

const FONT =
  'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans SC", "PingFang SC", sans-serif';

const CSS_PATH = 'src/app/globals.css';

/**
 * 从站点样式表**解析**主题令牌（唯一真相源 = globals.css）。
 * ⛔ 不在此硬编码色值：复制令牌即制造第二真相源，会随样式改动静默漂移。
 * 解析失败一律抛错（fail-closed），不退化到兜底色。
 */
function readThemeTokens(cssPath) {
  const css = readFileSync(cssPath, 'utf8');
  const blockOf = (pattern, label) => {
    const match = pattern.exec(css);
    if (!match) throw new Error(`globals.css 未解析到${label} —— 令牌是唯一真相源，⛔ 不硬编码兜底`);
    return match[1];
  };
  const light = blockOf(/:root\s*\{([^}]*)\}/, '浅色 :root 令牌块');
  const dark = blockOf(/:root\[data-theme='dark'\]\s*\{([^}]*)\}/, '深色令牌块');
  const pick = (block, token, where) => {
    const match = new RegExp(`${token}\\s*:\\s*([^;]+);`).exec(block);
    if (!match) throw new Error(`globals.css ${where} 块缺少令牌 ${token}`);
    return match[1].trim();
  };
  return {
    light: {
      ink: pick(light, '--text-primary', '浅色'),
      grid: pick(light, '--border-subtle', '浅色'),
      /// ★ 批二十点五：条形填充色＝品牌令牌（⛔ 不新增色值；条纹图**只由长度编码数值**）。
      accent: pick(light, '--brand-primary', '浅色'),
    },
    dark: {
      ink: pick(dark, '--text-primary', '深色'),
      grid: pick(dark, '--border-subtle', '深色'),
      accent: pick(dark, '--brand-primary', '深色'),
    },
  };
}

const TOKENS = readThemeTokens(CSS_PATH);

function parseArgs(argv) {
  const args = {
    metrics: 'src/data/metrics.json',
    catalog: 'src/data/projects.json',
    out: 'src/data/charts.json',
  };
  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i].replace(/^--/, '');
    if (!(key in args)) throw new Error(`未知参数 --${key}`);
    args[key] = argv[i + 1];
  }
  return args;
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (error) {
    throw new Error(`无法读取 ${path}：${error.message}（先跑 scripts/collect_metrics.py --write）`);
  }
}

/**
 * 剥掉 SSR 输出里的 `:hover` 规则（第十三批 W1 收口时**新暴露**的既有缺陷的修法）。
 *
 * 事实：echarts SVG-SSR 会为系列生成 `.zr0-cls-N:hover { cursor:pointer; fill:… }`
 *   —— 那是给**交互式** canvas/svg 图表用的强调样式。本站是**构建期 SSR → 纯静态导出**，
 *   这些「条」没有任何点击动作 ⇒ 悬停时 `cursor:pointer` + 变色＝**假可供性**
 *   （本站自有判据「悬停反馈面 ≡ 点击热区」明确禁止；`surface_hit_probe` 会判「错位」）。
 *
 * 为什么**删规则**而不是登记：`.zr0-cls-N` 的取值由 echarts 内部决定
 *   ⇒ 拿它当登记键＝会腐化的字面常量（图表一改就静默失效）。结构性做法是让它**不存在**。
 *
 * 悬停反馈由 `.chart__frame`（`data-spotlight="base"`，kind=decor）承担 —— 一致性也更好：
 * 反馈落在**框**上，而不是落在数据条上。
 *
 * ⛔ 只删含 `:hover` 的规则块；`<style>` 里其余规则原样保留（布局/字体依赖它们）。
 */
function stripHoverRules(svg) {
  let removed = 0;
  const out = svg.replace(/[^{}<>]*:hover[^{}<>]*\{[^{}]*\}/g, () => {
    removed += 1;
    return '';
  });
  if (removed) {
    process.stderr.write(`[charts] 剥离 SSR 生成的 :hover 规则 ${removed} 条（静态导出下无动作 ⇒ 假可供性）\n`);
  }
  return out;
}

/** 一次 SSR 渲染：三件套 init -> setOption -> renderToSVGString -> dispose。 */
function renderSvg(option, width, height) {
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width, height });
  chart.setOption(option);
  const svg = stripHoverRules(chart.renderToSVGString());
  chart.dispose(); // 必须：否则进程不退出
  return svg;
}

/**
 * ★ 批20.5：行标签 `name` 用**完整显示名**。
 *   原实现是 `truncate(title, 20)` —— 截断后的名字在本页**取不回**（图内无 `<title>`，
 *   轴标签又被 echarts 二次截断），属「截断即须可恢复」的反例。
 *   现由**重排（换行）**承担长度：轴标签宽度不变、允许多行，⛔ 不在数据侧预先丢字。
 *   ⇒ `truncate()` 随之无消费者，已删（⛔ 不留死代码）。
 */

/**
 * 图 1：DAG 图谱区「主入口图」实体数。
 * 主 scope := 各项目 figures[0]（采集定义里 json_assets 的顺序即主→次；B 级项目只有单 scope）。
 */
function mainEntryChart(metrics, catalog) {
  const titles = new Map((catalog.projects ?? []).map((p) => [p.name, p.title]));
  const rows = (metrics.projects ?? [])
    .filter((p) => p.section === 'dag' && p.status === 'ok')
    .map((p) => {
      const figure = (p.figures ?? [])[0];
      const value = figure?.entity_count;
      if (typeof value !== 'number' || value <= 0) return null;
      return {
        name: titles.get(p.name) ?? p.name,
        full: p.name,
        value,
        scope: figure.scope,
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.value - b.value);

  const width = 760;
  // ★ 批20.5：行高 38 → 48 —— 轴标签改「换行」后单行最多占 2 行（2 × 12px × 1.2 ≈ 29px），
  //   38px 会与相邻行贴到判据 S1（文字交叠）的边界 ⇒ 留出净距。
  const rowHeight = 48;
  const height = 48 + rows.length * rowHeight;

  const build = (theme) => {
    const accent = TOKENS[theme].accent;
    const ink = TOKENS[theme].ink;
    const grid = TOKENS[theme].grid;
    const option = {
      animation: false,
      backgroundColor: 'transparent',
      grid: { left: 168, right: 72, top: 10, bottom: 26, containLabel: false },
      xAxis: {
        type: 'value',
        axisLine: { show: true, lineStyle: { color: grid } },
        axisTick: { show: false },
        axisLabel: { color: ink, fontSize: 11 },
        splitLine: { show: true, lineStyle: { color: grid, type: 'dashed' } },
      },
      yAxis: {
        type: 'category',
        data: rows.map((row) => row.name),
        axisLine: { lineStyle: { color: grid } },
        axisTick: { show: false },
        // ★ 批20.5：`truncate` → `break`（换行）。原截断会让长名**不可恢复**（无 tooltip、
        //   无 `<title>`）；换行则完整显示，宽度不变 ⇒ ⛔ 不改绘图区几何。
        //   ⚠ 必须同时给 `lineHeight`：echarts 默认行高 = 字号（12px），而 12px 字形的渲染框
        //   高约 14px ⇒ 相邻两行的框**相交 14%**，会被本站既有判据 S1（文字交叠）判 FAIL
        //   （实测踩到）。行高 20px ⇒ 两行框之间有净距，S1 通过。
        axisLabel: { color: ink, fontSize: 12, width: 150, overflow: 'break', lineHeight: 20 },
      },
      series: [
        {
          type: 'bar',
          barWidth: 16,
          data: rows.map((row) => ({
            value: row.value,
            // ★ 批二十点五（F3 裁决）：**单色**。⛔ 不再按行序取色（那会造出「看起来像分类」的
            //   彩虹条，与图件 note 的「不解读为复杂度排序」相抵）。数值只由**长度**编码。
            itemStyle: { color: accent },
          })),
          label: {
            show: true,
            position: 'right',
            color: ink,
            fontSize: 12,
            formatter: '{c}',
          },
        },
      ],
      textStyle: { fontFamily: FONT, color: ink },
    };
    return renderSvg(option, width, height);
  };

  return {
    key: 'dag-main-entry-entities',
    title: 'DAG 图谱区 · 各项目主入口图的实体数',
    note:
      '口径：各项目「主入口图」的实体计数（主 scope := 该项目首个 scope）。' +
      '同名维度在各项目的实际用词不同（包 / 插件节点 / 知识点 / 方法节点…），' +
      // ★ 批20.5（本批新暴露的**既有**缺陷）：原文此处写 `**同区、同类 scope**`，
      //   而 `note` 是**纯文本**经 JSX 插入 `<p>`（⛔ 不经 Markdown 渲染）
      //   ⇒ 星号**字面显示**在页面上（实测 `out/stats/index.html` 命中 2 处 + `index.txt` 1 处）。
      //   修法＝去掉标记（⛔ 不改成 HTML 标签：JSX 会转义，反而又是一层看不出来的失败）。
      '故本图只作同区、同类 scope 的量级概览，⛔ 不跨区并比、不解读为复杂度排序。',
    width,
    height,
    rows,
    svg: { light: build('light'), dark: build('dark') },
  };
}

function main() {
  const args = parseArgs(process.argv);
  const metrics = readJson(args.metrics);
  const catalog = readJson(args.catalog);

  const charts = [mainEntryChart(metrics, catalog)].filter((chart) => chart.rows.length > 0);

  const payload = {
    schema_version: '1.0',
    generator: 'scripts/build_charts.mjs',
    capability_keys: ['echarts-declarative-chart-svg'],
    source: { metrics: args.metrics, metrics_as_of: metrics.as_of, catalog: args.catalog },
    charts,
  };

  mkdirSync(dirname(args.out), { recursive: true });
  writeFileSync(args.out, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');

  const summary = {
    status: 'ok',
    out: args.out,
    metrics_as_of: metrics.as_of,
    charts: charts.map((chart) => ({
      key: chart.key,
      rows: chart.rows.length,
      height: chart.height,
      light_bytes: Buffer.byteLength(chart.svg.light),
      dark_bytes: Buffer.byteLength(chart.svg.dark),
    })),
  };
  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
}

main();
