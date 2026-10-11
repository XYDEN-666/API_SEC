import type { ReactNode } from "react";
import { cx } from "../../lib/cx";

interface CardProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
  className?: string;
  bodyClassName?: string;
  interactive?: boolean;
  flush?: boolean;
}

export default function Card({
  title,
  subtitle,
  actions,
  footer,
  children,
  className,
  bodyClassName,
  interactive = false,
  flush = false,
}: CardProps) {
  const hasHeader = title !== undefined || subtitle !== undefined || actions !== undefined;
  return (
    <section
      className={cx("card", interactive && "card--interactive", className)}
    >
      {hasHeader && (
        <header className={cx("card__header", !children && !footer && "card__header--plain")}>
          <div className="stack stack--sm grow">
            {title !== undefined && <h3 className="card__title">{title}</h3>}
            {subtitle !== undefined && (
              <p className="card__subtitle">{subtitle}</p>
            )}
          </div>
          {actions !== undefined && <div className="card__actions">{actions}</div>}
        </header>
      )}
      {children !== undefined && (
        <div
          className={cx(
            "card__body",
            flush && "card__body--flush",
            bodyClassName,
          )}
        >
          {children}
        </div>
      )}
      {footer !== undefined && <footer className="card__footer">{footer}</footer>}
    </section>
  );
}

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: "accent" | "info" | "warning" | "danger" | "success";
  hint?: ReactNode;
}

export function StatCard({
  label,
  value,
  icon,
  tone = "accent",
  hint,
}: StatCardProps) {
  return (
    <div className="stat-card">
      {icon !== undefined && (
        <span
          className={cx(
            "stat-card__icon",
            tone !== "accent" && `stat-card__icon--${tone}`,
          )}
          aria-hidden="true"
        >
          {icon}
        </span>
      )}
      <div className="stack stack--sm">
        <span className="stat-card__value">{value}</span>
        <span className="stat-card__label">{label}</span>
        {hint !== undefined && <span className="tiny subtle">{hint}</span>}
      </div>
    </div>
  );
}
