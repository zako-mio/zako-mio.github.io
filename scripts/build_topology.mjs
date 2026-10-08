#!/usr/bin/env node
/**
 * 图谱拓扑计算（2b-5）· 构建期 headless，产物为**静态数据**。
 *
 * 能力层取用：`cytoscape-js-graph-topology`
 * 记录分工（⛔ 不可越界）：
 *   select_when —— 「把图当**数据结构**做拓扑计算与断言」，运行在**构建期 / 服务端**（Node）；
 *   reject_when —— 「需要开箱即用的**交互画布** ＋ 内置物理布局」⇒ 应取 vis-network（该候选**未入层**）。
 *   ⇒ 故这里只做 headless 拓扑计算，把结果以**静态文字/数值**嵌进详情页。
 *      ⛔ 不在浏览器里拿它当画布用；也不为此引入未入层的依赖。
 *   记录实测：headless 下 `cy.container()` 为 null、`cy.png()` 抛
 *   「A headless instance can not render images」——本用法不触碰该路径。
 *
 * 记录 usage.requires_config 的硬约束（违反会静默出错）：
 *   1. 必须显式 `headless: true`
 *   2. `data.id` 必须唯一且显式（构造期重复 id 会被**静默去重**；缺 id 会自动生成 UUID）
 *   3. 边端点必须齐全：悬挂边**直接抛错**（这点对我们是好事 —— 上游数据结构问题会 fail-closed 暴露）
 *   4. headless 布局不自动运行（本脚本不依赖布局，故不触发）
 *
 * ★ 交叉校验（防两份定义漂移）：图上重算的 node/edge 数必须等于 `metrics.json`
 *   里对应 scope 已登记的 entity_count / relation_count，不符即退出非零。
 *
 * ★ 派生纪律：产物不含运行时钟，只带上游 as_of ⇒ 幂等。
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

import cytoscape from 'cytoscape';

/** 图资产清单：项目 -> 站点相对路径 -> 结构字段（与 collect_metrics.py 的 json_assets 对应）。 */
const GRAPH_SOURCES = [
  {
    project: 'deepseek-harness-plugin-dag',
    scope: '插件级（全量重建 v0.1.7-rc.2）',
    asset: '01-dag-data/webapp-dag.json',
    nodes: [['nodes']],
    edges: [['edges']],
    self_report: { acyclic: ['meta', 'acyclic'] },
  },
  {
    project: 'opencode-dag-analysis',
    scope: '图1 官方 DAG',
    asset: '01-dag-data/official-dag.json',
    nodes: [['nodes']],
    edges: [['edges']],
    self_report: { acyclic: ['stats', 'has_cycle'], invert: true },
  },
  {
    project: 'opencode-dag-analysis',
    scope: '图2 对比 DAG',
    asset: '01-dag-data/diff-dag.json',
    nodes: [['nodes']],
    edges: [['edges']],
    self_report: { acyclic: ['stats', 'has_cycle'], invert: true },
  },
  {
    project: 'opencode-dag-analysis',
    scope: '图3 改造双层 DAG',
    asset: '01-dag-data/modified-dag.json',
    nodes: [['nodes']],
    edges: [['edges']],
    self_report: { acyclic: ['stats', 'has_cycle'], invert: true },
  },
  {
    project: 'dsh-manager-analysis',
    scope: '插件级（术语自成一格）',
    asset: '02-analysis/dag-data.json',
    nodes: [['nodes'], ['stubs']],
    edges: [['edges_core']],
  },
];

const DEFAULT_BASE = 'https://zako-mio.github.io';

function parseArgs(argv) {
  const args = {
    metrics: 'src/data/metrics.json',
    out: 'src/data/topology.json',
    base: DEFAULT_BASE,
    offlineDir: null,
  };
  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i].replace(/^--/, '');
    if (!(key in args)) throw new Error(`未知参数 --${key}`);
    args[key] = argv[i + 1];
  }
  return args;
}

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

/** 取嵌套路径（如 ['meta','x']）。 */
function pick(object, path) {
  return path.reduce((current, key) => (current == null ? undefined : current[key]), object);
}

async function loadGraphDocument(source, args) {
  // 离线模式：本地已有抓取副本时优先用（构建期默认走网络）
  if (args.offlineDir) {
    const name = `${source.project}_${source.asset.replaceAll('/', '_')}`;
    return readJson(`${args.offlineDir}/${name}`);
  }
  const url = `${args.base}/${source.project}/${source.asset}`;
  const response = await fetch(url, { headers: { 'user-agent': 'zako-mio-topology-builder' } });
  if (!response.ok) throw new Error(`抓取失败 ${url} -> HTTP ${response.status}`);
  return response.json();
}

/** 最长路径分层（Kahn）：层号 = 该节点最长前置链长度；有环时返回 null。 */
function longestPathLayers(nodes, edges) {
  const indegree = new Map(nodes.map((id) => [id, 0]));
  const outgoing = new Map(nodes.map((id) => [id, []]));
  for (const edge of edges) {
    if (!indegree.has(edge.from) || !indegree.has(edge.to)) continue;
    indegree.set(edge.to, indegree.get(edge.to) + 1);
    outgoing.get(edge.from).push(edge.to);
  }
  const layer = new Map(nodes.map((id) => [id, 0]));
  const queue = nodes.filter((id) => indegree.get(id) === 0);
  let visited = 0;
  while (queue.length > 0) {
    const current = queue.shift();
    visited += 1;
    for (const next of outgoing.get(current)) {
      layer.set(next, Math.max(layer.get(next), layer.get(current) + 1));
      indegree.set(next, indegree.get(next) - 1);
      if (indegree.get(next) === 0) queue.push(next);
    }
  }
  if (visited !== nodes.length) return null; // 有环
  return Math.max(...layer.values()) + 1;
}

/** 找到一条具体的有向环（DFS back-edge），用于在「自称无环」与实测不符时给出可复核证据。 */
function findCycle(nodes, edges) {
  const adjacency = new Map();
  for (const edge of edges) {
    if (!adjacency.has(edge.from)) adjacency.set(edge.from, []);
    adjacency.get(edge.from).push(edge.to);
  }
  const WHITE = 0, GRAY = 1, BLACK = 2;
  const color = new Map(nodes.map((id) => [id, WHITE]));
  const stack = [];
  let cycle = null;
  const visit = (id) => {
    color.set(id, GRAY);
    stack.push(id);
    for (const next of adjacency.get(id) ?? []) {
      if (!color.has(next)) continue;
      if (color.get(next) === GRAY) {
        cycle = stack.slice(stack.indexOf(next));
        return true;
      }
      if (color.get(next) === WHITE && visit(next)) return true;
    }
    stack.pop();
    color.set(id, BLACK);
    return false;
  };
  for (const id of nodes) {
    if (color.get(id) === WHITE && visit(id)) break;
  }
  return cycle;
}

function analyse(document, source) {
  const nodeRecords = source.nodes.flatMap((path) => pick(document, path) ?? []);
  const edgeRecords = source.edges.flatMap((path) => pick(document, path) ?? []);

  const ids = nodeRecords.map((node) => node.id).filter(Boolean);
  const duplicated = ids.filter((id, index) => ids.indexOf(id) !== index);
  if (duplicated.length > 0) {
    // 记录实测：构造期重复 id 会被**静默去重** —— 我们不容忍静默，直接报错
    throw new Error(`${source.project}/${source.scope}：节点 id 重复（会被 cytoscape 静默去重）：${[...new Set(duplicated)].slice(0, 5)}`);
  }
  for (const node of nodeRecords) {
    if (!node.id) throw new Error(`${source.project}/${source.scope}：存在缺 id 的节点（会被自动生成 UUID）`);
  }

  const elements = [
    ...ids.map((id) => ({ data: { id } })),
    ...edgeRecords.map((edge, index) => ({
      data: { id: `e${index}`, source: edge.from, target: edge.to },
    })),
  ];

  // headless:true 必填（记录 requires_config 第 1 条）；悬挂边在此会抛错 => fail-closed
  const cy = cytoscape({ headless: true, elements });

  const pairs = edgeRecords.map((edge) => ({ from: edge.from, to: edge.to }));
  // 口径对齐：上游明文声明「type-only 类型导入边标注但**不参与分层**（TS 类型环合法）」
  // ⇒ 分层只吃非 type_only 边；⛔ 若把 type-only 边算进去，会把合法类型环误报成「图有环」。
  const layerPairs = edgeRecords
    .filter((edge) => edge.type_only !== true)
    .map((edge) => ({ from: edge.from, to: edge.to }));
  const layers = longestPathLayers(ids, layerPairs);

  const degrees = ids
    .map((id) => ({ id, degree: cy.getElementById(id).degree() }))
    .sort((a, b) => b.degree - a.degree || a.id.localeCompare(b.id));

  // 介数：记录实测「裸 id 会被当作非法选择器、返回 0 且只在 stderr 告警」=> 必须传 `#id`；
  // 而含 CSS 特殊字符的 id 无法安全成选择器 => 显式留空并说明，⛔ 不写 0。
  const SAFE_ID = /^[A-Za-z0-9_-]+$/;
  const unsafeIds = ids.filter((id) => !SAFE_ID.test(id));
  const betweenness = cy.elements().betweennessCentrality({ directed: true });
  const topBetweenness = unsafeIds.length > 0
    ? null
    : ids
        .map((id) => ({ id, score: Number(betweenness.betweenness(`#${id}`).toFixed(4)) }))
        .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
        .slice(0, 3);

  return {
    node_count: cy.nodes().length,
    edge_count: cy.edges().length,
    layer_edge_count: layerPairs.length,
    layer_note:
      edgeRecords.length === layerPairs.length
        ? '全部边参与分层'
        : `分层排除 ${edgeRecords.length - layerPairs.length} 条 type-only 边（上游声明其不参与分层）`,
    component_count: cy.elements().components().length,
    acyclic: layers !== null,
    longest_path_layers: layers,
    cycle_sample: layers === null ? (findCycle(ids, layerPairs) ?? []).slice(0, 8) : null,
    top_degree: degrees.slice(0, 5),
    top_betweenness: topBetweenness,
    betweenness_skipped_ids: unsafeIds.length,
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const metrics = readJson(args.metrics);
  const declared = new Map();
  for (const entry of metrics.projects) {
    for (const figure of entry.figures) {
      declared.set(`${entry.name}::${figure.scope}`, figure);
    }
  }

  const results = [];
  for (const source of GRAPH_SOURCES) {
    const document = await loadGraphDocument(source, args);
    const analysis = analyse(document, source);
    const figure = declared.get(`${source.project}::${source.scope}`);
    if (!figure) {
      throw new Error(`${source.project}/${source.scope}：metrics.json 中无对应 scope（两份定义漂移）`);
    }
    if (figure.entity_count != null && figure.entity_count !== analysis.node_count) {
      throw new Error(
        `${source.project}/${source.scope}：图上节点数 ${analysis.node_count} ≠ metrics 登记 ${figure.entity_count}`,
      );
    }
    if (figure.relation_count != null && figure.relation_count !== analysis.edge_count) {
      throw new Error(
        `${source.project}/${source.scope}：图上边数 ${analysis.edge_count} ≠ metrics 登记 ${figure.relation_count}`,
      );
    }
    const selfReportPath = source.self_report?.acyclic;
    const rawClaim = selfReportPath ? pick(document, selfReportPath) : undefined;
    const acyclicClaim =
      typeof rawClaim === 'boolean' ? (source.self_report.invert ? !rawClaim : rawClaim) : null;

    results.push({
      project: source.project,
      scope: source.scope,
      asset: source.asset,
      url: `${args.base}/${source.project}/${source.asset}`,
      analysis,
      claimed: {
        // 上游自述（供「自称 vs 实测」并陈；⛔ 不代上游改）
        layer_count: figure.layer_count ?? null,
        acyclic: acyclicClaim,
      },
      // 自称与实测是否一致（null = 上游未自述该项）
      agreement: {
        acyclic:
          acyclicClaim === null ? null : acyclicClaim === analysis.acyclic,
        layers:
          figure.layer_count == null || analysis.longest_path_layers == null
            ? null
            : figure.layer_count === analysis.longest_path_layers,
      },
    });
  }

  const payload = {
    schema_version: '1.0',
    generator: 'scripts/build_topology.mjs',
    capability_keys: ['cytoscape-js-graph-topology'],
    mode: 'headless 拓扑计算（⛔ 非画布渲染）',
    source: { metrics: args.metrics, metrics_as_of: metrics.as_of },
    graphs: results,
  };

  mkdirSync(dirname(args.out), { recursive: true });
  writeFileSync(args.out, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');

  process.stdout.write(
    `${JSON.stringify(
      {
        status: 'ok',
        out: args.out,
        graphs: results.map((item) => ({
          project: item.project,
          scope: item.scope,
          nodes: item.analysis.node_count,
          edges: item.analysis.edge_count,
          components: item.analysis.component_count,
          acyclic: item.analysis.acyclic,
          longest_path_layers: item.analysis.longest_path_layers,
          claimed_layers: item.claimed.layer_count,
        })),
      },
      null,
      2,
    )}\n`,
  );
}

main().catch((error) => {
  process.stderr.write(`拓扑计算失败：${error.message}\n`);
  process.exit(1);
});
