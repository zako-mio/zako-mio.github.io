'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { ProjectCard, searchBlobOf } from './ProjectCard';
import { DOMAIN_LABELS, TYPE_LABELS, type Project } from '@/lib/schema';

type SortKey = 'updated' | 'name' | 'stars';
type ViewKey = 'grid' | 'list' | 'group';

const SORT_OPTIONS: Array<{ value: SortKey; label: string }> = [
  { value: 'updated', label: '最近更新' },
  { value: 'name', label: '名称' },
  { value: 'stars', label: '星标' },
];

const VIEW_OPTIONS: Array<{ value: ViewKey; label: string }> = [
  { value: 'grid', label: '网格' },
  { value: 'list', label: '列表' },
  { value: 'group', label: '按类型分组' },
];

const UNLABELLED = '未标注';

export interface WorksExplorerProps {
  projects: Project[];
}

function readStateFromUrl() {
  if (typeof window === 'undefined') return null;
  const params = new URLSearchParams(window.location.search);
  const list = (key: string) =>
    (params.get(key) ?? '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
  const sort = params.get('sort');
  const view = params.get('view');
  return {
    q: params.get('q') ?? '',
    types: list('type'),
    domains: list('domain'),
    languages: list('lang'),
    sort: (SORT_OPTIONS.some((option) => option.value === sort) ? sort : 'updated') as SortKey,
    view: (VIEW_OPTIONS.some((option) => option.value === view) ? view : 'grid') as ViewKey,
  };
}

function writeStateToUrl(state: {
  q: string;
  types: string[];
  domains: string[];
  languages: string[];
  sort: SortKey;
  view: ViewKey;
}) {
  if (typeof window === 'undefined') return;
  const params = new URLSearchParams();
  if (state.q) params.set('q', state.q);
  if (state.types.length) params.set('type', state.types.join(','));
  if (state.domains.length) params.set('domain', state.domains.join(','));
  if (state.languages.length) params.set('lang', state.languages.join(','));
  if (state.sort !== 'updated') params.set('sort', state.sort);
  if (state.view !== 'grid') params.set('view', state.view);
  const query = params.toString();
  const url = `${window.location.pathname}${query ? `?${query}` : ''}`;
  window.history.replaceState(null, '', url);
}

/**
 * 作品索引：多维筛选 ＋ 关键词搜索 ＋ 排序 ＋ 视图切换，全部状态进 URL。
 *
 * ★ 本轮强推荐四项中的三项在此落地：
 *   - 筛选态进 URL（可分享 / 可回退；用 replaceState 避免污染历史栈）
 *   - 排序切换
 *   - （卡片嵌套修复在 ProjectCard）
 * ★ 无 JS 降级：客户端组件同样参与 SSR，首屏 HTML 含**全部**项目卡；
 *   筛选/排序/视图需要 JS，故附 noscript 说明。⛔ 不得把初始渲染改为「先空列表」。
 */
export function WorksExplorer({ projects }: WorksExplorerProps) {
  const [query, setQuery] = useState('');
  const [types, setTypes] = useState<string[]>([]);
  const [domains, setDomains] = useState<string[]>([]);
  const [languages, setLanguages] = useState<string[]>([]);
  const [sort, setSort] = useState<SortKey>('updated');
  const [view, setView] = useState<ViewKey>('grid');

  useEffect(() => {
    const initial = readStateFromUrl();
    if (!initial) return;
    setQuery(initial.q);
    setTypes(initial.types);
    setDomains(initial.domains);
    setLanguages(initial.languages);
    setSort(initial.sort);
    setView(initial.view);
  }, []);

  useEffect(() => {
    writeStateToUrl({ q: query, types, domains, languages, sort, view });
  }, [query, types, domains, languages, sort, view]);

  const blobs = useMemo(
    () => new Map(projects.map((project) => [project.name, searchBlobOf(project)])),
    [projects],
  );

  const typeFacets = useMemo(
    () =>
      Object.entries(TYPE_LABELS)
        .filter(([value]) => projects.some((project) => project.type === value))
        .map(([value, label]) => ({ value, label })),
    [projects],
  );

  const domainFacets = useMemo(
    () =>
      Object.entries(DOMAIN_LABELS)
        .filter(([value]) => projects.some((project) => project.domains.includes(value as never)))
        .map(([value, label]) => ({ value, label })),
    [projects],
  );

  const languageFacets = useMemo(() => {
    const set = new Set(projects.map((project) => project.language ?? UNLABELLED));
    return [...set].sort((a, b) => a.localeCompare(b)).map((value) => ({ value, label: value }));
  }, [projects]);

  const matches = useCallback(
    (
      project: Project,
      overrides?: { skipGroup?: 'type' | 'domain' | 'lang'; value?: string },
    ) => {
      const needle = query.trim().toLowerCase();
      if (needle && !(blobs.get(project.name) ?? '').includes(needle)) return false;

      const language = project.language ?? UNLABELLED;
      const skip = overrides?.skipGroup;
      const value = overrides?.value;

      const typeOk =
        skip === 'type' ? project.type === value : types.length === 0 || types.includes(project.type);
      const domainOk =
        skip === 'domain'
          ? project.domains.includes(value as never)
          : domains.length === 0 || project.domains.some((domain) => domains.includes(domain));
      const langOk =
        skip === 'lang' ? language === value : languages.length === 0 || languages.includes(language);

      return typeOk && domainOk && langOk;
    },
    [blobs, query, types, domains, languages],
  );

  const visible = useMemo(() => {
    const list = projects.filter((project) => matches(project));
    return [...list].sort((a, b) => {
      if (sort === 'name') return a.title.localeCompare(b.title, 'zh-Hans-CN');
      if (sort === 'stars') return (b.stars ?? 0) - (a.stars ?? 0) || a.name.localeCompare(b.name);
      const pushedA = a.pushed_at ?? '';
      const pushedB = b.pushed_at ?? '';
      if (pushedA !== pushedB) return pushedB.localeCompare(pushedA);
      return a.name.localeCompare(b.name);
    });
  }, [projects, matches, sort]);

  const grouped = useMemo(() => {
    if (view !== 'group') return null;
    const groups = new Map<string, Project[]>();
    for (const project of visible) {
      const key = project.type;
      const bucket = groups.get(key);
      if (bucket) bucket.push(project);
      else groups.set(key, [project]);
    }
    return [...groups.entries()];
  }, [view, visible]);

  const countFor = useCallback(
    (group: 'type' | 'domain' | 'lang', value: string) =>
      projects.filter((project) => matches(project, { skipGroup: group, value })).length,
    [projects, matches],
  );

  const toggle = (
    list: string[],
    setList: (next: string[]) => void,
    value: string,
  ) => {
    setList(list.includes(value) ? list.filter((item) => item !== value) : [...list, value]);
  };

  const reset = () => {
    setQuery('');
    setTypes([]);
    setDomains([]);
    setLanguages([]);
    setSort('updated');
    setView('grid');
  };

  const renderFacetRow = (
    legend: string,
    group: 'type' | 'domain' | 'lang',
    facets: Array<{ value: string; label: string }>,
    selected: string[],
    setSelected: (next: string[]) => void,
    idPrefix: string,
  ) => {
    if (facets.length === 0) return null;
    return (
      <div className="filterbar__row">
        <span className="filterbar__legend" id={`${idPrefix}-label`}>
          {legend}
        </span>
        <div className="filterbar__chips" role="group" aria-labelledby={`${idPrefix}-label`}>
          {facets.map((facet) => (
            <button
              className="chip"
              type="button"
              key={facet.value}
              aria-pressed={selected.includes(facet.value)}
              onClick={() => toggle(selected, setSelected, facet.value)}
            >
              {facet.label}
              <span className="chip__count">{countFor(group, facet.value)}</span>
            </button>
          ))}
        </div>
      </div>
    );
  };

  const isFiltered =
    query.trim() !== '' || types.length > 0 || domains.length > 0 || languages.length > 0;

  return (
    <div className="explorer">
      <div className="filterbar" role="group" aria-label="项目筛选与搜索">
        <div className="filterbar__search">
          <label className="visually-hidden" htmlFor="project-search">
            关键词搜索项目
          </label>
          <input
            id="project-search"
            className="filterbar__input"
            type="search"
            placeholder="搜索项目标题、摘要或标签…"
            autoComplete="off"
            spellCheck={false}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>

        {renderFacetRow('类型', 'type', typeFacets, types, setTypes, 'filter-type')}
        {renderFacetRow('领域', 'domain', domainFacets, domains, setDomains, 'filter-domain')}
        {renderFacetRow('语言', 'lang', languageFacets, languages, setLanguages, 'filter-lang')}

        <div className="filterbar__row filterbar__row--controls">
          <span className="filterbar__legend" id="filter-sort-label">
            排序
          </span>
          <div className="filterbar__chips" role="group" aria-labelledby="filter-sort-label">
            {SORT_OPTIONS.map((option) => (
              <button
                className="chip"
                type="button"
                key={option.value}
                aria-pressed={sort === option.value}
                onClick={() => setSort(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>

          <span className="filterbar__legend" id="filter-view-label">
            视图
          </span>
          <div className="filterbar__chips" role="group" aria-labelledby="filter-view-label">
            {VIEW_OPTIONS.map((option) => (
              <button
                className="chip"
                type="button"
                key={option.value}
                aria-pressed={view === option.value}
                onClick={() => setView(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="filterbar__status">
          <span className="filterbar__count" aria-live="polite" role="status">
            显示 {visible.length} / {projects.length} 个项目
          </span>
          <button className="chip" type="button" onClick={reset} disabled={!isFiltered}>
            重置筛选
          </button>
        </div>
      </div>

      <noscript>
        <p className="explorer__noscript">
          筛选、排序与视图切换需要 JavaScript。已为你展开全部 {projects.length} 个项目。
        </p>
      </noscript>

      {visible.length === 0 ? (
        <p className="empty-state">没有匹配的项目。试试更换筛选条件或清空关键词。</p>
      ) : view === 'group' && grouped ? (
        <div className="works-grouped">
          {grouped.map(([type, items]) => (
            <section className="works-group" key={type}>
              <h3 className="works-group__title">
                {TYPE_LABELS[type as keyof typeof TYPE_LABELS] ?? type}
                <span className="works-group__count">{items.length}</span>
              </h3>
              <div className="projects-grid">
                {items.map((project) => (
                  <ProjectCard project={project} key={project.name} />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className={view === 'list' ? 'projects-grid projects-grid--list' : 'projects-grid'}>
          {visible.map((project) => (
            <ProjectCard project={project} key={project.name} />
          ))}
        </div>
      )}
    </div>
  );
}
