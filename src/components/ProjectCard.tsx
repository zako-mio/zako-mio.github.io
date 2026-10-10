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
   * ⚠ 必须是**显式 opt-in**，只给**服务端一次渲染、不再变动**的网格开启。
   *
   * ★ 第十二批订正（原文写的是「`MotionRuntime` 只在挂载时扫描一次 ⇒ 动态节点会永远停在
   *   隐藏态」）：那个**根因已被修掉** —— 运行时现由 `MutationObserver` **持续接管**新出现的
   *   `[data-reveal]`，动态插入的节点不会再卡死。
   *   ⚠ 但本参数**仍保持 opt-in**，理由已变：`/works` 的卡片由筛选器**反复重渲染**，
   *   若也打上 `data-reveal`，每次筛选都会让全部卡片**重播一次进场动画**（含错峰延迟），
   *   那是观感噪声、不是缺陷修复；且会把 M1（单页 `[data-reveal]` ≤32）逼近上界。
   *   ⇒ 需要给 `/works` 开进场时**先与用户裁决**，⛔ 不要顺手打开。
   *   （改这里必须同步改实现，两处状态指针不许各自漂移。）
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
      data-spotlight="base"
      data-reveal={reveal ? '' : undefined}
      style={reveal ? ({ '--i': index } as CSSProperties) : undefined}
    >
      <div className="card__body">
        <ul className="card__tags">
          <li className="chip chip--type" data-spotlight="micro">{typeLabel}</li>
          {domainLabels.map((label) => (
            <li className="chip" data-spotlight="micro" key={label}>
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
            <span className="chip chip--warning" data-spotlight="micro" title="未启用 GitHub Pages，仅提供仓库入口">
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
