import type { CSSProperties } from 'react';

import Link from 'next/link';

import { ProjectRecency } from './figures/ProjectRecency';

import type { RecencyRange } from '@/lib/recency';
import { DOMAIN_LABELS, TYPE_LABELS, type Project } from '@/lib/schema';

export interface ProjectCardProps {
  project: Project;
  /**
   * 是否参与滚动进场（默认 false）。
   *
   * ⚠ 必须是**显式 opt-in**：`/works` 的卡片由客户端筛选器重渲染，
   *   而 `MotionRuntime` 只在挂载时扫描一次 `[data-reveal]`。
   *   若给这类动态重渲染的卡片也打上 `data-reveal`，
   *   筛选后新出现的卡片会永远停在隐藏态（静默的「筛选完是空白」）。
   *   ⇒ 只给**服务端一次渲染、不再变动**的网格开启。
   */
  reveal?: boolean;
  /** 同屏进场的错峰序号（CSS 变量 `--i`），仅在同批渲染的静态网格里有意义。 */
  index?: number;
  /**
   * 卡片上「活跃度标尺」的共享时间跨度，由服务端页面算好传下来。
   * 为 null / 缺省 ⇒ 不画标尺（⛔ 不拿中点冒充位置）。
   */
  range?: RecencyRange | null;
}

export function searchBlobOf(project: Project): string {
  return [
    project.title,
    project.name,
    project.summary,
    TYPE_LABELS[project.type],
    ...project.domains.map((domain) => DOMAIN_LABELS[domain]),
    project.language ?? '',
  ]
    .join(' ')
    .toLowerCase();
}

/**
 * 项目卡。
 *
 * ★ 卡片嵌套交互修复（第三批）：取消原先覆盖整卡的 `::after` 层，
 *   改为「标题 → 站内详情页」＋「页脚 → 外链」两处显式可点目标。
 * ★ 第五批新增 `ProjectRecency`：把「这件事还在不在动」画成标尺，
 *   补的是卡片原本缺失的一维（相对活跃度），⛔ 不是把已有文字改个画法。
 */
export function ProjectCard({
  project,
  reveal = false,
  index = 0,
  range = null,
}: ProjectCardProps) {
  const typeLabel = TYPE_LABELS[project.type];
  const domainLabels = project.domains.map((domain) => DOMAIN_LABELS[domain]);

  return (
    <article
      className="card"
      data-reveal={reveal ? '' : undefined}
      style={reveal ? ({ '--i': index } as CSSProperties) : undefined}
    >
      <div className="card__body">
        <ul className="card__tags">
          <li className="chip chip--type">{typeLabel}</li>
          {domainLabels.map((label) => (
            <li className="chip" key={label}>
              {label}
            </li>
          ))}
        </ul>

        <h3 className="card__title">
          <Link href={`/works/${project.name}`}>{project.title}</Link>
        </h3>

        <p className="card__summary">{project.summary}</p>

        <ProjectRecency project={project} range={range} />
      </div>

      <footer className="card__footer">
        <p className="card__meta">
          {project.language ? <span className="card__lang">{project.language}</span> : null}
          {typeof project.stars === 'number' ? (
            <span aria-label={`${project.stars} stars`}>★ {project.stars}</span>
          ) : null}
          {!project.has_pages ? (
            <span className="chip chip--warning" title="未启用 GitHub Pages，仅提供仓库入口">
              仅仓库
            </span>
          ) : null}
        </p>
        <p className="card__links">
          {project.has_pages ? (
            <a className="button button--small" href={project.entry_url} rel="noopener noreferrer" target="_blank">
              在线预览
            </a>
          ) : null}
          <a className="button button--small" href={project.repo_url} rel="noopener noreferrer" target="_blank">
            仓库
          </a>
        </p>
      </footer>
    </article>
  );
}
