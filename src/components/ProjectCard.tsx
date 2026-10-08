import Link from 'next/link';

import { DOMAIN_LABELS, TYPE_LABELS, type Project } from '@/lib/schema';

export interface ProjectCardProps {
  project: Project;
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
 * ★ 卡片嵌套交互修复（本轮）：取消原先覆盖整卡的 `::after` 层，
 *   改为「标题 → 站内详情页」＋「页脚 → 外链」两处显式可点目标，
 *   消除「整卡链接 / 在线预览 / 仓库」三层交互区叠置对键盘与屏幕阅读器的干扰。
 *   整卡的悬停/聚焦浮起效果保留（由 .card:hover / :focus-within 提供）。
 */
export function ProjectCard({ project }: ProjectCardProps) {
  const typeLabel = TYPE_LABELS[project.type];
  const domainLabels = project.domains.map((domain) => DOMAIN_LABELS[domain]);

  return (
    <article className="card">
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
            <a href={project.entry_url} rel="noopener noreferrer" target="_blank">
              在线预览
            </a>
          ) : null}
          <a href={project.repo_url} rel="noopener noreferrer" target="_blank">
            仓库
          </a>
        </p>
      </footer>
    </article>
  );
}
