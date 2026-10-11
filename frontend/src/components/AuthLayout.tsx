import type { ReactNode } from "react";
import Icon from "./Icon";

const HIGHLIGHTS = [
  {
    title: "Six built-in scanners",
    text: "Security headers, CORS, HTTP methods, JWT configuration, SQLi indicators and IDOR/BOLA multi-identity replay.",
  },
  {
    title: "OWASP API Top 10 (2023) mapping",
    text: "Every finding carries a category and a 0–10 risk score derived from severity and confidence.",
  },
  {
    title: "Reports that travel",
    text: "Review findings in the app, then export the same data as HTML, PDF or JSON.",
  },
];

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

/** Two-column shell used by the login and registration screens. */
export default function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: AuthLayoutProps) {
  return (
    <div className="auth-layout">
      <section className="auth-hero">
        <div className="auth-hero__brand">
          <span className="brand__mark" aria-hidden="true">
            <Icon name="shield-check" size={22} strokeWidth={1.9} />
          </span>
          <span className="brand__text">
            <span className="brand__name">APIShield</span>
            <span className="brand__tag">API security assessment</span>
          </span>
        </div>

        <h2 className="auth-hero__title">
          Find API security gaps before someone else does.
        </h2>
        <p className="auth-hero__subtitle">
          Import an OpenAPI 3.x spec, replay it through the scanner suite, and
          triage the results with OWASP API Top 10 context and exportable
          reports.
        </p>

        <ul className="auth-hero__list">
          {HIGHLIGHTS.map((item) => (
            <li className="auth-hero__item" key={item.title}>
              <Icon name="check" size={17} />
              <div>
                <strong>{item.title}</strong>
                <p>{item.text}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="auth-panel">
        <div
          className="stack stack--lg"
          style={{ width: "100%", maxWidth: "26rem" }}
        >
          <div className="auth-mobile-brand">
            <span className="brand__mark" aria-hidden="true">
              <Icon name="shield-check" size={22} strokeWidth={1.9} />
            </span>
            <span className="brand__name" style={{ color: "var(--text)" }}>
              APIShield
            </span>
          </div>
          <div className="card">
            <header className="card__header card__header--plain">
              <div className="stack stack--sm">
                <h1 className="card__title">{title}</h1>
                <p className="card__subtitle">{subtitle}</p>
              </div>
            </header>
            <div className="card__body">{children}</div>
          </div>
          <p className="auth-card__links">{footer}</p>
        </div>
      </section>
    </div>
  );
}
