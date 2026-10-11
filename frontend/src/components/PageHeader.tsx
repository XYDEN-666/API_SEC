import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export interface Crumb {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  title: ReactNode;
  subtitle?: ReactNode;
  breadcrumbs?: Crumb[];
  actions?: ReactNode;
}

export default function PageHeader({
  title,
  subtitle,
  breadcrumbs,
  actions,
}: PageHeaderProps) {
  return (
    <div className="stack">
      {breadcrumbs !== undefined && breadcrumbs.length > 0 && (
        <nav className="breadcrumbs" aria-label="Breadcrumb">
          {breadcrumbs.map((crumb, index) => (
            <span key={`${crumb.label}-${index}`} className="row">
              {index > 0 && (
                <span className="breadcrumbs__sep" aria-hidden="true">
                  /
                </span>
              )}
              {crumb.to !== undefined ? (
                <Link to={crumb.to}>{crumb.label}</Link>
              ) : (
                <span>{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="page-header">
        <div className="page-header__text">
          <h1>{title}</h1>
          {subtitle !== undefined && <p className="muted">{subtitle}</p>}
        </div>
        {actions !== undefined && (
          <div className="page-header__actions">{actions}</div>
        )}
      </div>
    </div>
  );
}
