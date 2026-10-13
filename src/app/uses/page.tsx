import type { Metadata } from 'next';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const metadata: Metadata = {
  title: '在用',
  description:
    '本站正在使用的技术栈：逐条取自仓库 package.json 的依赖名、版本字面量与它在本站承担什么，不写无法在仓库里回源的内容。',
  alternates: { canonical: '/uses' },
};

/**
 * 「在用」页（新一轮新增）。
 *
 * ★ 单一真相源：`src/data/uses.json`（版本逐条照抄 package.json 的字面值）。
 *   本页只负责**呈现**，⛔ 不在 TSX 里再写一份依赖清单 —— 那会让版本出现第二处真相源，
 *   与本站「同一事实只写一处」的既有口径（见 /about 的注释与 gate_ia_division）一致。
 *
 * ★ 降级（照 src/lib/site.ts / src/lib/catalog.ts 的体例）：数据缺失、JSON 解析失败、
 *   字段类型不对，一律**不抛错**，退化为空状态并把原因写在页面上。
 *   ⛔ 页面构建期必须永远成功：本页是静态导出的一屏，抛错会连累整次构建。
 */
interface UsesItem {
  name: string;
  version: string;
  note: string;
}

interface UsesGroup {
  id: string;
  title: string;
  items: UsesItem[];
}

interface UsesDoc {
  schema_version: string;
  as_of: string;
  intro: string;
  groups: UsesGroup[];
}

interface UsesResult {
  doc: UsesDoc;
  ok: boolean;
  hint: string | null;
}

const DATA_PATH = 'src/data/uses.json';

const MISSING_HINT =
  '技术栈数据尚未就位（src/data/uses.json 缺失或为空）。补齐该文件后重新构建即可显示本页。';

const INVALID_HINT =
  '技术栈数据未通过解析校验，已临时降级为空状态；修复 src/data/uses.json 后重新构建即可恢复。';

const EMPTY: UsesDoc = { schema_version: '', as_of: '', intro: '', groups: [] };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

/** 逐字段收窄：任何一处不合契约即返回 null（由调用方降级），⛔ 不做「部分渲染」。 */
function parseDoc(raw: unknown): UsesDoc | null {
  if (!isRecord(raw)) return null;
  if (!Array.isArray(raw.groups)) return null;

  // ⚠ 用**显式类型的局部变量 + 下标循环**（⛔ 不在收窄后的 `any[]` 上调 `.entries()`）：
  //   既让类型确定，也避开 lint 的 unsafe-any 类规则。
  const groupsRaw: unknown[] = raw.groups;

  const groups: UsesGroup[] = [];
  for (let groupIndex = 0; groupIndex < groupsRaw.length; groupIndex += 1) {
    const groupRaw: unknown = groupsRaw[groupIndex];
    if (!isRecord(groupRaw)) continue;
    const title = asString(groupRaw.title);
    if (!title) continue;
    if (!Array.isArray(groupRaw.items)) continue;

    const itemsRaw: unknown[] = groupRaw.items;

    const items: UsesItem[] = [];
    for (let itemIndex = 0; itemIndex < itemsRaw.length; itemIndex += 1) {
      const itemRaw: unknown = itemsRaw[itemIndex];
      if (!isRecord(itemRaw)) continue;
      const name = asString(itemRaw.name);
      if (!name) continue;
      items.push({
        name,
        version: asString(itemRaw.version),
        note: asString(itemRaw.note),
      });
    }
    if (items.length === 0) continue;

    // DOM id 由**下标**派生（⛔ 不用数据里的 id 直接拼进 id 属性）：
    // 数据件里出现重复或带空格的 id 时，页面结构仍然成立。
    groups.push({
      id: `uses-group-${groupIndex + 1}`,
      title,
      items,
    });
  }

  if (groups.length === 0) return null;

  return {
    schema_version: asString(raw.schema_version),
    as_of: asString(raw.as_of),
    intro: asString(raw.intro),
    groups,
  };
}

function loadUses(): UsesResult {
  try {
    const abs = resolve(process.cwd(), DATA_PATH);
    if (!existsSync(abs)) return { doc: EMPTY, ok: false, hint: MISSING_HINT };
    const raw = readFileSync(abs, 'utf8');
    if (!raw.trim()) return { doc: EMPTY, ok: false, hint: MISSING_HINT };
    const parsed = parseDoc(JSON.parse(raw) as unknown);
    if (!parsed) return { doc: EMPTY, ok: false, hint: INVALID_HINT };
    return { doc: parsed, ok: true, hint: null };
  } catch {
    return { doc: EMPTY, ok: false, hint: INVALID_HINT };
  }
}

export default function UsesPage() {
  const { doc, ok, hint } = loadUses();

  return (
    <section className="section">
      <div className="container">
        <header className="section__head">
          {/* ★ 层级：h1（本页）→ h2（分组）→ h3（每个依赖）—— 逐级下降，⛔ 不跳级 */}
          <h1 className="section__title">在用</h1>
          <p className="section__subtitle">
            本站正在使用的技术栈 · 逐条取自仓库 package.json
          </p>
        </header>

        {ok ? (
          <>
            {doc.intro ? <p className="uses__intro">{doc.intro}</p> : null}

            <div className="uses__groups">
              {doc.groups.map((group) => (
                <section className="uses__group" key={group.id} aria-labelledby={`${group.id}-title`}>
                  <h2 className="uses__group-title" id={`${group.id}-title`}>
                    {group.title}
                  </h2>
                  <ul className="uses__list">
                    {group.items.map((item) => (
                      <li className="uses__item" key={`${group.id}-${item.name}`}>
                        <h3 className="uses__name">
                          <span className="uses__pkg">{item.name}</span>
                          {item.version ? <span className="uses__version">{item.version}</span> : null}
                        </h3>
                        {item.note ? <p className="uses__note">{item.note}</p> : null}
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>

            {doc.as_of ? (
              <p className="page__footnote">数据 as_of {doc.as_of} · 版本照抄 package.json 字面值</p>
            ) : null}
          </>
        ) : (
          <p className="empty-state">{hint ?? MISSING_HINT}</p>
        )}
      </div>
    </section>
  );
}
