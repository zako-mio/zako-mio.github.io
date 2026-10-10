import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * 术语解释层的读取层（第十四批 W2）。
 *
 * ★ 单一真相源＝`src/data/glossary.json`（⛔ 解释性文字只此一处，不得在组件里另写）。
 * ★ **fail-closed**（⛔ 不给兜底默认值）：与本仓库其它 loader 不同——
 *   `site.config.json` 缺了可以按约定取默认，但**解释层的默认值会变成第二真相源**
 *   （正是本能力要消灭的东西）⇒ 文件缺失/损坏/字段缺失一律**构建期抛错**。
 *   同口径先例：`src/lib/build-notes.ts` 的 `loadGateManifest()`。
 * ★ 索引在**进程内**建一次（构建期多页复用），键＝`id` ＋ 全部 `aliases`（查表用）。
 */

export interface GlossaryEntry {
  id: string;
  term: string;
  aliases?: string[];
  definition: string;
  boundary: string;
  source: string;
  surfaces?: string[];
}

interface GlossaryFile {
  schema_version?: number;
  note?: string;
  as_of?: string;
  terms: GlossaryEntry[];
}

const GLOSSARY_PATH = 'src/data/glossary.json';

let index: Map<string, GlossaryEntry> | null = null;

function buildIndex(): Map<string, GlossaryEntry> {
  const raw = readFileSync(resolve(process.cwd(), GLOSSARY_PATH), 'utf8');
  const parsed = JSON.parse(raw) as GlossaryFile;
  if (!Array.isArray(parsed.terms) || parsed.terms.length === 0) {
    throw new Error(`${GLOSSARY_PATH}: terms 必须为非空数组`);
  }
  const map = new Map<string, GlossaryEntry>();
  for (const entry of parsed.terms) {
    for (const field of ['id', 'term', 'definition', 'boundary', 'source'] as const) {
      if (!entry[field] || typeof entry[field] !== 'string') {
        throw new Error(`${GLOSSARY_PATH}: 条目 ${entry.id ?? '(无 id)'} 缺字段 ${field}`);
      }
    }
    // ⛔ 键冲突＝两条不同解释指向同一写法 ⇒ 正是要消灭的「第二处解释」，构建期直接失败。
    for (const key of [entry.id, entry.term, ...(entry.aliases ?? [])]) {
      const prev = map.get(key);
      if (prev && prev.id !== entry.id) {
        throw new Error(`${GLOSSARY_PATH}: 键 ${JSON.stringify(key)} 同时指向 ${prev.id} 与 ${entry.id}`);
      }
      map.set(key, entry);
    }
  }
  return map;
}

/** 按 `id`（或 `term`/`aliases`）取条目。⛔ 取不到即抛错 —— 组件引用了不存在的术语属构建期缺陷。 */
export function glossaryEntry(id: string): GlossaryEntry {
  if (!index) index = buildIndex();
  const entry = index.get(id);
  if (!entry) throw new Error(`glossary: 未知术语 ${JSON.stringify(id)}（${GLOSSARY_PATH} 中无此 id/别名）`);
  return entry;
}

/** 已登记术语数（供门控/报告取用；⛔ 不在页面里写死这个数）。 */
export function glossarySize(): number {
  if (!index) index = buildIndex();
  return new Set([...index.values()].map((e) => e.id)).size;
}
