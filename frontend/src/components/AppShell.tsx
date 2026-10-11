import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { API_BASE_URL, getHealth } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useAsyncData } from "../hooks/useAsyncData";
import { useTheme } from "../hooks/useTheme";
import { initialsFromEmail } from "../lib/format";
import Button from "./ui/Button";
import Icon from "./Icon";
import { cx } from "../lib/cx";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "dashboard" as const, end: true },
  { to: "/projects", label: "Projects", icon: "folder" as const, end: false },
];

/** Section name shown in the top bar, derived from the current route. */
function sectionLabel(pathname: string): string {
  if (pathname === "/") {
    return "Dashboard";
  }
  if (pathname.startsWith("/projects")) {
    return "Projects";
  }
  if (pathname.includes("/scans/")) {
    return "Scan results";
  }
  if (pathname.startsWith("/targets")) {
    return "Target";
  }
  return "APIShield";
}

export default function AppShell() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const health = useAsyncData(() => getHealth(), []);

  // The sidebar is an overlay below 980px; close it on navigation.
  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  const apiOnline = health.data?.status === "ok";

  return (
    <div className="app-shell">
      {navOpen && (
        <button
          type="button"
          className="sidebar__scrim"
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
        />
      )}

      <aside className={cx("sidebar", navOpen && "is-open")}>
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            <Icon name="shield-check" size={22} strokeWidth={1.9} />
          </span>
          <span className="brand__text">
            <span className="brand__name">APIShield</span>
            <span className="brand__tag">API security assessment</span>
          </span>
        </div>

        <nav className="sidebar__nav" aria-label="Main">
          <span className="sidebar__section-label">Workspace</span>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cx("nav-link", isActive && "is-active")
              }
            >
              <span className="nav-link__icon">
                <Icon name={item.icon} size={17} />
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__spacer" />

        <div className="sidebar__card">
          <span className="sidebar__card-title">Backend</span>
          <span className="sidebar__card-text">{API_BASE_URL}</span>
          <span className="health-dot">
            <span
              className={cx(
                "health-dot__dot",
                !apiOnline && "health-dot__dot--down",
              )}
              aria-hidden="true"
            />
            {health.loading
              ? "Checking…"
              : apiOnline
                ? "API reachable"
                : "API unreachable"}
          </span>
          {!health.loading && !apiOnline && (
            <Button size="sm" variant="ghost" onClick={health.reload}>
              Retry
            </Button>
          )}
        </div>

        <div className="sidebar__footer">
          <div className="row">
            <span className="avatar" aria-hidden="true">
              {initialsFromEmail(user?.email)}
            </span>
            <span className="stack stack--sm grow">
              <span className="truncate small strong" title={user?.email}>
                {user?.email}
              </span>
              <span className="tiny subtle">{user?.role ?? "member"}</span>
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            icon={<Icon name="logout" size={15} />}
          >
            Sign out
          </Button>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <Button
            variant="ghost"
            iconOnly
            className="nav-toggle"
            aria-label="Open navigation"
            onClick={() => setNavOpen(true)}
            icon={<Icon name="menu" size={18} />}
          />
          <div className="topbar__heading">
            <span className="topbar__eyebrow">Workspace</span>
            <span className="topbar__title">
              {sectionLabel(location.pathname)}
            </span>
          </div>
          <div className="topbar__actions">
            <div className="theme-toggle" role="group" aria-label="Colour theme">
              <button
                type="button"
                className={cx(
                  "theme-toggle__option",
                  theme === "light" && "is-active",
                )}
                onClick={() => setTheme("light")}
                aria-label="Light theme"
                aria-pressed={theme === "light"}
              >
                <Icon name="sun" size={15} />
              </button>
              <button
                type="button"
                className={cx(
                  "theme-toggle__option",
                  theme === "dark" && "is-active",
                )}
                onClick={() => setTheme("dark")}
                aria-label="Dark theme"
                aria-pressed={theme === "dark"}
              >
                <Icon name="moon" size={15} />
              </button>
            </div>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
