/**
 * Inline SVG icon set. Keeping the icons in the bundle (instead of pulling an
 * icon package or a webfont) means the UI renders identically offline.
 */

export type IconName =
  | "activity"
  | "alert"
  | "arrow-left"
  | "check"
  | "chevron-down"
  | "chevron-left"
  | "chevron-right"
  | "clock"
  | "close"
  | "copy"
  | "dashboard"
  | "download"
  | "edit"
  | "external"
  | "eye"
  | "eye-off"
  | "file"
  | "filter"
  | "folder"
  | "globe"
  | "info"
  | "key"
  | "layers"
  | "link"
  | "list"
  | "lock"
  | "logout"
  | "menu"
  | "moon"
  | "play"
  | "plus"
  | "refresh"
  | "search"
  | "shield"
  | "shield-check"
  | "sparkles"
  | "sun"
  | "target"
  | "trash"
  | "upload"
  | "user";

const PATHS: Record<IconName, JSX.Element> = {
  activity: <path d="M3 12h4l2.5-6.5L14 18l2-6h5" />,
  alert: (
    <>
      <path d="M12 4.2 20.6 19H3.4z" />
      <path d="M12 10v4.2" />
      <path d="M12 17.1h.01" />
    </>
  ),
  "arrow-left": (
    <>
      <path d="M11 5.5 4.5 12 11 18.5" />
      <path d="M4.5 12H20" />
    </>
  ),
  check: <path d="M5 12.6 9.4 17 19 7" />,
  "chevron-down": <path d="M6.5 9.5 12 15l5.5-5.5" />,
  "chevron-left": <path d="M14.5 6.5 9 12l5.5 5.5" />,
  "chevron-right": <path d="M9.5 6.5 15 12l-5.5 5.5" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="8.4" />
      <path d="M12 7.4V12l3 1.9" />
    </>
  ),
  close: <path d="M6.4 6.4 17.6 17.6M17.6 6.4 6.4 17.6" />,
  copy: (
    <>
      <rect x="9" y="9" width="11" height="11" rx="2.2" />
      <path d="M15.2 6.4V5.2A1.2 1.2 0 0 0 14 4H5.2A1.2 1.2 0 0 0 4 5.2V14a1.2 1.2 0 0 0 1.2 1.2h1.2" />
    </>
  ),
  dashboard: (
    <>
      <rect x="3.2" y="3.2" width="7.4" height="9" rx="1.6" />
      <rect x="13.4" y="3.2" width="7.4" height="5" rx="1.6" />
      <rect x="13.4" y="11.4" width="7.4" height="9.4" rx="1.6" />
      <rect x="3.2" y="15.4" width="7.4" height="5.4" rx="1.6" />
    </>
  ),
  download: (
    <>
      <path d="M12 4v11" />
      <path d="M7.8 11.6 12 15.8l4.2-4.2" />
      <path d="M4.8 19.6h14.4" />
    </>
  ),
  edit: (
    <>
      <path d="M4 20h4.2L19 9.2a2.3 2.3 0 0 0-3.2-3.2L5 16.8z" />
      <path d="M14.6 6.6l2.8 2.8" />
    </>
  ),
  external: (
    <>
      <path d="M14 4h6v6" />
      <path d="M20 4l-8.8 8.8" />
      <path d="M18 14.2V19a1.2 1.2 0 0 1-1.2 1.2H5.2A1.2 1.2 0 0 1 4 19V7.2A1.2 1.2 0 0 1 5.2 6h4.6" />
    </>
  ),
  eye: (
    <>
      <path d="M2.6 12S6.2 6.4 12 6.4 21.4 12 21.4 12 17.8 17.6 12 17.6 2.6 12 2.6 12z" />
      <circle cx="12" cy="12" r="2.9" />
    </>
  ),
  "eye-off": (
    <>
      <path d="M4 4l16 16" />
      <path d="M9.6 5.9A9.7 9.7 0 0 1 12 5.6c5.8 0 9.4 5.6 9.4 5.6a17 17 0 0 1-3.3 3.9" />
      <path d="M6.4 7.7A16.7 16.7 0 0 0 2.6 11.2s3.6 5.6 9.4 5.6a9.4 9.4 0 0 0 3.6-.7" />
      <path d="M10.1 10.2a2.7 2.7 0 0 0 3.7 3.8" />
    </>
  ),
  file: (
    <>
      <path d="M14 3.6H7.4A1.8 1.8 0 0 0 5.6 5.4v13.2a1.8 1.8 0 0 0 1.8 1.8h9.2a1.8 1.8 0 0 0 1.8-1.8V8z" />
      <path d="M14 3.6V8h4.8" />
    </>
  ),
  filter: (
    <>
      <path d="M3.4 5.4h17.2" />
      <path d="M6.6 12h10.8" />
      <path d="M10 18.6h4" />
    </>
  ),
  folder: (
    <path d="M3.4 7.2A2.2 2.2 0 0 1 5.6 5h3.2a2 2 0 0 1 1.5.7l1.3 1.5h7A2.2 2.2 0 0 1 20.6 9.4v7.4a2.2 2.2 0 0 1-2.2 2.2H5.6a2.2 2.2 0 0 1-2.2-2.2z" />
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="8.4" />
      <path d="M3.6 12h16.8" />
      <path d="M12 3.6c2.4 2.4 3.6 5.2 3.6 8.4S14.4 18 12 20.4C9.6 18 8.4 15.2 8.4 12S9.6 6 12 3.6z" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="8.4" />
      <path d="M12 11.2v5" />
      <path d="M12 7.9h.01" />
    </>
  ),
  key: (
    <>
      <circle cx="8.2" cy="15" r="3.4" />
      <path d="M10.7 12.6 20 3.4" />
      <path d="M16.6 6.8l2 2" />
      <path d="M14 9.4l2 2" />
    </>
  ),
  layers: (
    <>
      <path d="M12 3.4 20.4 8 12 12.6 3.6 8z" />
      <path d="M3.6 12.6 12 17.2l8.4-4.6" />
    </>
  ),
  link: (
    <>
      <path d="M10.2 13.8a3.9 3.9 0 0 0 5.5 0l2.6-2.6a3.9 3.9 0 0 0-5.5-5.5l-1 1" />
      <path d="M13.8 10.2a3.9 3.9 0 0 0-5.5 0l-2.6 2.6a3.9 3.9 0 0 0 5.5 5.5l1-1" />
    </>
  ),
  list: (
    <>
      <path d="M8.4 6.4h11.2M8.4 12h11.2M8.4 17.6h11.2" />
      <path d="M4.2 6.4h.01M4.2 12h.01M4.2 17.6h.01" />
    </>
  ),
  lock: (
    <>
      <rect x="4.6" y="10.2" width="14.8" height="9.4" rx="2.2" />
      <path d="M8.4 10.2V7.6a3.6 3.6 0 0 1 7.2 0v2.6" />
    </>
  ),
  logout: (
    <>
      <path d="M15 4.4h3.4A1.6 1.6 0 0 1 20 6v12a1.6 1.6 0 0 1-1.6 1.6H15" />
      <path d="M11 8 7 12l4 4" />
      <path d="M7 12h8.6" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  moon: <path d="M20 14.4A8.4 8.4 0 0 1 9.6 4 8.4 8.4 0 1 0 20 14.4z" />,
  play: <path d="M7.4 5.2 18.6 12 7.4 18.8z" />,
  plus: <path d="M12 5.2v13.6M5.2 12h13.6" />,
  refresh: (
    <>
      <path d="M20 11.4A8 8 0 1 0 17.8 17" />
      <path d="M20 5.4v6h-6" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.4" />
      <path d="M15.8 15.8 20.6 20.6" />
    </>
  ),
  shield: (
    <path d="M12 3.4 19 6.2v5.3c0 4.2-2.9 7.9-7 9.1-4.1-1.2-7-4.9-7-9.1V6.2z" />
  ),
  "shield-check": (
    <>
      <path d="M12 3.4 19 6.2v5.3c0 4.2-2.9 7.9-7 9.1-4.1-1.2-7-4.9-7-9.1V6.2z" />
      <path d="M9.1 12.1 11.2 14.2l4-4.2" />
    </>
  ),
  sparkles: (
    <>
      <path d="M11 4.4l1.5 4.1 4.1 1.5-4.1 1.5L11 15.6 9.5 11.5 5.4 10l4.1-1.5z" />
      <path d="M17.6 15.4l.7 1.9 1.9.7-1.9.7-.7 1.9-.7-1.9-1.9-.7 1.9-.7z" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.6v2.2M12 19.2v2.2M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2.6 12h2.2M19.2 12h2.2M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="8.2" />
      <circle cx="12" cy="12" r="3.4" />
      <path d="M12 1.8v2.4M12 19.8v2.4M1.8 12h2.4M19.8 12h2.4" />
    </>
  ),
  trash: (
    <>
      <path d="M4.4 7h15.2" />
      <path d="M9.4 7V5.4a1.2 1.2 0 0 1 1.2-1.2h2.8a1.2 1.2 0 0 1 1.2 1.2V7" />
      <path d="M6.4 7l.9 12.1a1.4 1.4 0 0 0 1.4 1.3h6.6a1.4 1.4 0 0 0 1.4-1.3L17.6 7" />
      <path d="M10.4 11v6M13.6 11v6" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V4.6" />
      <path d="M7.8 8.8 12 4.6l4.2 4.2" />
      <path d="M4.8 19.6h14.4" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8.4" r="3.6" />
      <path d="M5 20a7 7 0 0 1 14 0" />
    </>
  ),
};

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  strokeWidth?: number;
}

export default function Icon({
  name,
  size = 18,
  className,
  strokeWidth = 1.7,
}: IconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}
