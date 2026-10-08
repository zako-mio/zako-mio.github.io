#!/usr/bin/env node
/**
 * E 指标图表生成（2b-4）· 构建期 Node SSR → SVG。
 *
 * 能力层取用：`echarts-declarative-chart-svg` ＋ `d3-scale-chromatic-schemes`
 * （记录见 ~/.config/opencode/lib/frontend-capability/records/<key>.json；调用协议见 call.md）
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
import { schemeTableau10, schemeSet2 } from 'd3-scale-chromatic';

const FONT =
  'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans SC", "PingFang SC", sans-serif';

/** 双模色板（能力层 d3-scale-chromatic-schemes）：浅色底用 Tableau10，深色底用 Set2（更亮）。 */
const PALETTE = { light: schemeTableau10, dark: schemeSet2 };

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
    },
    dark: {
      ink: pick(dark, '--text-primary', '深色'),
      grid: pick(dark, '--border-subtle', '深色'),
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

/** 一次 SSR 渲染：三件套 init -> setOption -> renderToSVGString -> dispose。 */
function renderSvg(option, width, height) {
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width, height });
  chart.setOption(option);
  const svg = chart.renderToSVGString();
  chart.dispose(); // 必须：否则进程不退出
  return svg;
}

function truncate(text, max) {
  const value = String(text ?? '');
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

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
        name: truncate(titles.get(p.name) ?? p.name, 20),
        full: p.name,
        value,
        scope: figure.scope,
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.value - b.value);

  const width = 760;
  const rowHeight = 38;
  const height = 48 + rows.length * rowHeight;

  const build = (theme) => {
    const palette = PALETTE[theme];
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
        axisLabel: { color: ink, fontSize: 12, width: 150, overflow: 'truncate' },
      },
      series: [
        {
          type: 'bar',
          barWidth: 16,
          data: rows.map((row, index) => ({
            value: row.value,
            itemStyle: { color: palette[index % palette.length] },
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
      '故本图只作**同区、同类 scope** 的量级概览，⛔ 不跨区并比、不解读为复杂度排序。',
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
    capability_keys: ['echarts-declarative-chart-svg', 'd3-scale-chromatic-schemes'],
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
