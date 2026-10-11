/**
 * Formatting helpers (dates, durations, numbers, identifiers).
 *
 * Pure functions that take an explicit "now" where relevant, so tests are
 * deterministic. Free of React and browser-only APIs.
 */

function toDate(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const date = value instanceof Date ? value : new Date(String(value));
  return Number.isNaN(date.getTime()) ? null : date;
}

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const relativeFormatter = new Intl.RelativeTimeFormat(undefined, {
  numeric: "auto",
});

const UNITS = [
  { limit: 60, unit: "second", ms: 1000 },
  { limit: 60, unit: "minute", ms: 60 * 1000 },
  { limit: 24, unit: "hour", ms: 60 * 60 * 1000 },
  { limit: 30, unit: "day", ms: 24 * 60 * 60 * 1000 },
  { limit: 12, unit: "month", ms: 30 * 24 * 60 * 60 * 1000 },
  { limit: Number.POSITIVE_INFINITY, unit: "year", ms: 365 * 24 * 60 * 60 * 1000 },
];

/** Locale date + time, or an em dash when the value is missing. */
export function formatDateTime(value) {
  const date = toDate(value);
  return date === null ? "—" : dateTimeFormatter.format(date);
}

/** Locale date only, or an em dash when the value is missing. */
export function formatDate(value) {
  const date = toDate(value);
  return date === null ? "—" : dateFormatter.format(date);
}

/**
 * Human relative time such as "3 minutes ago" or "just now".
 * @param {string|Date|null|undefined} value
 * @param {Date} [now] Reference instant, defaults to the current time.
 */
export function formatRelative(value, now = new Date()) {
  const date = toDate(value);
  if (date === null) {
    return "—";
  }
  const deltaMs = date.getTime() - now.getTime();
  const absMs = Math.abs(deltaMs);
  if (absMs < 45 * 1000) {
    return "just now";
  }
  for (const { limit, unit, ms } of UNITS) {
    const amount = deltaMs / ms;
    if (Math.abs(amount) < limit) {
      return relativeFormatter.format(Math.round(amount), unit);
    }
  }
  return formatDate(date);
}

/**
 * Elapsed time between two instants, e.g. "1.2s", "43s", "2m 07s".
 * Returns null while the end instant is unknown.
 */
export function formatDuration(start, end) {
  const from = toDate(start);
  const to = toDate(end);
  if (from === null || to === null) {
    return null;
  }
  const seconds = Math.max(0, (to.getTime() - from.getTime()) / 1000);
  if (seconds < 10) {
    return `${seconds.toFixed(1)}s`;
  }
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes}m ${String(remainder).padStart(2, "0")}s`;
}

/** Thousands-separated integer. */
export function formatNumber(value) {
  return new Intl.NumberFormat().format(value);
}

/**
 * "1 project" / "3 projects".
 * @param {number} count
 * @param {string} singular
 * @param {string} [plural] Defaults to `singular + "s"`.
 */
export function pluralize(count, singular, plural = `${singular}s`) {
  return `${formatNumber(count)} ${count === 1 ? singular : plural}`;
}

/** Up to two initials from an email address or display name. */
export function initialsFromEmail(value) {
  const local = String(value ?? "").split("@")[0] ?? "";
  const parts = local.split(/[._\-+]+/).filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

/** Shorten long identifiers from the middle. */
export function truncateMiddle(value, max = 42) {
  const text = String(value ?? "");
  if (text.length <= max) {
    return text;
  }
  const keep = Math.floor((max - 1) / 2);
  return `${text.slice(0, keep)}…${text.slice(text.length - keep)}`;
}

/** Capitalise the first letter of a lowercase token. */
export function capitalize(value) {
  const text = String(value ?? "");
  return text === "" ? text : text.charAt(0).toUpperCase() + text.slice(1);
}
