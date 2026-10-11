import type { ReactNode } from "react";
import { cx } from "../../lib/cx";
import Icon, { type IconName } from "../Icon";

interface EmptyStateProps {
  icon?: IconName;
  title: string;
  text?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ icon = "sparkles", title, text, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon">
        <Icon name={icon} size={20} />
      </span>
      <p className="empty-state__title">{title}</p>
      {text !== undefined && <p className="empty-state__text">{text}</p>}
      {action !== undefined && <div className="row">{action}</div>}
    </div>
  );
}

export function Skeleton({
  width,
  className,
}: {
  width?: string;
  className?: string;
}) {
  return (
    <span
      className={cx("skeleton", "skeleton--text", className)}
      style={width !== undefined ? { width } : undefined}
      aria-hidden="true"
    />
  );
}

/** Placeholder rows shown while a table or list is loading. */
export function SkeletonList({ rows = 4 }: { rows?: number }) {
  return (
    <div className="skeleton-stack" aria-hidden="true">
      {Array.from({ length: rows }, (_, index) => (
        <span className="skeleton skeleton--card" key={index} />
      ))}
    </div>
  );
}

interface ErrorAlertProps {
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}

export function ErrorAlert({
  title = "Something went wrong",
  children,
  action,
}: ErrorAlertProps) {
  return (
    <div className="alert alert--error" role="alert">
      <span className="alert__icon">
        <Icon name="alert" size={17} />
      </span>
      <div className="stack stack--sm grow">
        <span className="alert__title">{title}</span>
        <p>{children}</p>
        {action !== undefined && <div className="row">{action}</div>}
      </div>
    </div>
  );
}

interface InfoAlertProps {
  tone?: "info" | "warning" | "success";
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}

export function InfoAlert({
  tone = "info",
  title,
  children,
  action,
}: InfoAlertProps) {
  const icon: IconName = tone === "warning" ? "alert" : tone === "success" ? "check" : "info";
  return (
    <div className={cx("alert", `alert--${tone}`)}>
      <span className="alert__icon">
        <Icon name={icon} size={17} />
      </span>
      <div className="stack stack--sm grow">
        {title !== undefined && <span className="alert__title">{title}</span>}
        <div>{children}</div>
        {action !== undefined && <div className="row">{action}</div>}
      </div>
    </div>
  );
}
