/**
 * Domain vocabulary and pure aggregation helpers for the APIShield UI.
 *
 * Everything here is free of React and browser APIs so it can be exercised
 * directly by `node --test` (see frontend/tests/domain.test.mjs). Values that
 * must agree with the backend (severity names, scan statuses, OWASP labels,
 * risk bands, password bounds) are documented next to their counterpart in
 * backend/app so the two stay in sync.
 */

/**
 * @typedef {object} FindingLike
 * @property {string} severity
 * @property {string} title
 * @property {string} description
 * @property {string} endpoint
 * @property {string} owasp_category
 * @property {string} confidence
 * @property {number} risk_score
 */

/** Severity values, most severe first (backend `Severity` enum). */
export const SEVERITIES = ["critical", "high", "medium", "low", "info"];

/** Sort weight per severity, most severe first. @type {Record<string, number>} */
export const SEVERITY_ORDER = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

/** @type {Record<string, string>} */
export const SEVERITY_LABEL = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

/**
 * Chart colours for the severity scale. These intentionally mirror the
 * `--sev-*` design tokens and the backend HTML report palette.
 * @type {Record<string, string>}
 */
export const SEVERITY_HEX = {
  critical: "#b91c1c",
  high: "#ea580c",
  medium: "#b45309",
  low: "#15803d",
  info: "#475569",
};

/** Scan statuses emitted by the orchestrator. @type {Record<string, string>} */
export const STATUS_LABEL = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  completed_with_errors: "Completed with errors",
  failed: "Failed",
};

/** Statuses that mean the scan is still in flight. */
export const ACTIVE_STATUSES = ["queued", "running"];

/** Statuses that mean the scan will not change again without a re-run. */
export const FINISHED_STATUSES = ["completed", "completed_with_errors", "failed"];

/** OWASP API Security Top 10 (2023) labels, mirroring owasp_mapping.py. */
export const OWASP_CATEGORIES = [
  { code: "api1:2023", short: "API1", label: "Broken Object Level Authorization" },
  { code: "api2:2023", short: "API2", label: "Broken Authentication" },
  {
    code: "api3:2023",
    short: "API3",
    label: "Broken Object Property Level Authorization",
  },
  { code: "api4:2023", short: "API4", label: "Unrestricted Resource Consumption" },
  {
    code: "api5:2023",
    short: "API5",
    label: "Broken Function Level Authorization",
  },
  {
    code: "api6:2023",
    short: "API6",
    label: "Unrestricted Access to Sensitive Business Flows",
  },
  { code: "api7:2023", short: "API7", label: "Server-Side Request Forgery" },
  { code: "api8:2023", short: "API8", label: "Security Misconfiguration" },
  { code: "api9:2023", short: "API9", label: "Improper Inventory Management" },
  { code: "api10:2023", short: "API10", label: "Unsafe Consumption of APIs" },
];

/** @type {Record<string, {code: string, short: string, label: string}>} */
const OWASP_BY_CODE = {};
for (const category of OWASP_CATEGORIES) {
  OWASP_BY_CODE[category.code] = category;
}

/** Order index of a severity; unknown values sort last. */
export function severityRank(severity) {
  const rank = SEVERITY_ORDER[severity];
  return rank === undefined ? SEVERITIES.length : rank;
}

/** Display label for a severity value. */
export function severityLabel(severity) {
  return SEVERITY_LABEL[severity] ?? severity;
}

/** Chart colour for a severity value. */
export function severityColor(severity) {
  return SEVERITY_HEX[severity] ?? SEVERITY_HEX.info;
}

/** Display label for a scan status value. */
export function statusLabel(status) {
  return STATUS_LABEL[status] ?? status;
}

/** True while a scan is queued or running. */
export function isScanActive(status) {
  return ACTIVE_STATUSES.includes(status);
}

/** True once a scan has reached a terminal status. */
export function isScanFinished(status) {
  return FINISHED_STATUSES.includes(status);
}

/** Short OWASP label, e.g. "api1:2023" -> "API1". */
export function owaspShort(code) {
  const known = OWASP_BY_CODE[code];
  if (known !== undefined) {
    return known.short;
  }
  return code.split(":")[0].toUpperCase();
}

/** Full OWASP label, e.g. "api1:2023" -> "API1:2023 Broken Object ...". */
export function owaspLabel(code) {
  const known = OWASP_BY_CODE[code];
  if (known !== undefined) {
    return `${known.short}:2023 ${known.label}`;
  }
  return code;
}

/**
 * Risk band for a 0-10 score. Bands and their inclusive lower bounds mirror
 * backend/app/services/risk_scoring.py.
 */
export function riskBand(score) {
  if (score >= 8) {
    return "critical";
  }
  if (score >= 6) {
    return "high";
  }
  if (score >= 4) {
    return "medium";
  }
  return "low";
}

/** Display label for a confidence value. */
export function confidenceLabel(confidence) {
  if (confidence === "high") {
    return "High confidence";
  }
  if (confidence === "medium") {
    return "Medium confidence";
  }
  if (confidence === "low") {
    return "Low confidence";
  }
  return confidence;
}

/**
 * Count findings per severity plus the total.
 * @param {FindingLike[]} findings
 * @returns {{critical: number, high: number, medium: number, low: number, info: number, total: number}}
 */
export function summarizeFindings(findings) {
  /** @type {Record<string, number>} */
  const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  for (const finding of findings) {
    if (counts[finding.severity] === undefined) {
      counts[finding.severity] = 0;
    }
    counts[finding.severity] += 1;
  }
  return {
    critical: counts.critical,
    high: counts.high,
    medium: counts.medium,
    low: counts.low,
    info: counts.info,
    total: findings.length,
  };
}

/**
 * Severity rows for a chart or legend, ordered most severe first and always
 * including empty severities so the scale stays stable between scans.
 * @param {FindingLike[]} findings
 */
export function severityBreakdown(findings) {
  const counts = summarizeFindings(findings);
  return SEVERITIES.map((severity) => ({
    severity,
    label: severityLabel(severity),
    color: severityColor(severity),
    count: /** @type {number} */ (
      counts[/** @type {keyof typeof counts} */ (severity)]
    ),
  }));
}

/**
 * Finding counts grouped by OWASP category, ordered by the category number
 * then descending count.
 * @param {FindingLike[]} findings
 */
export function categoryBreakdown(findings) {
  /** @type {Record<string, number>} */
  const counts = {};
  for (const finding of findings) {
    counts[finding.owasp_category] = (counts[finding.owasp_category] ?? 0) + 1;
  }
  return categoryBreakdownFromCounts(counts);
}

/**
 * Category rows from a `code -> count` map, as returned by the dashboard
 * aggregate endpoint.
 * @param {Record<string, number>} counts
 */
export function categoryBreakdownFromCounts(counts) {
  return Object.keys(counts)
    .map((code) => ({
      code,
      short: owaspShort(code),
      label: owaspLabel(code),
      count: counts[code] ?? 0,
      index: OWASP_CATEGORIES.findIndex((item) => item.code === code),
    }))
    .sort((a, b) => {
      const aIndex = a.index === -1 ? OWASP_CATEGORIES.length : a.index;
      const bIndex = b.index === -1 ? OWASP_CATEGORIES.length : b.index;
      return aIndex - bIndex || b.count - a.count;
    });
}

/**
 * Case-insensitive search across the fields an analyst scans by eye.
 * @param {FindingLike} finding
 * @param {string} query
 */
function matchesQuery(finding, query) {
  const haystack = [
    finding.title,
    finding.description,
    finding.endpoint,
    finding.severity,
    severityLabel(finding.severity),
    finding.owasp_category,
    owaspLabel(finding.owasp_category),
    finding.confidence,
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query);
}

/**
 * Filter findings by free-text query, severity set and OWASP category.
 * An empty `severities` array means "all severities".
 * @template {FindingLike} T
 * @param {T[]} findings
 * @param {{query?: string, severities?: string[], category?: string|null}} [filters]
 * @returns {T[]}
 */
export function filterFindings(findings, filters = {}) {
  const query = (filters.query ?? "").trim().toLowerCase();
  const severities = filters.severities ?? [];
  const category = filters.category ?? null;

  return findings.filter((finding) => {
    if (severities.length > 0 && !severities.includes(finding.severity)) {
      return false;
    }
    if (category !== null && finding.owasp_category !== category) {
      return false;
    }
    if (query !== "" && !matchesQuery(finding, query)) {
      return false;
    }
    return true;
  });
}

/**
 * Sort findings by severity (default), risk score, endpoint or title.
 * Ties fall back to the risk score, then to the endpoint so ordering is stable.
 * @template {FindingLike} T
 * @param {T[]} findings
 * @param {"severity"|"risk"|"endpoint"|"title"} [key]
 * @returns {T[]}
 */
export function sortFindings(findings, key = "severity") {
  const byRisk = (a, b) => b.risk_score - a.risk_score;
  const rows = [...findings];
  if (key === "risk") {
    return rows.sort((a, b) => byRisk(a, b) || a.title.localeCompare(b.title));
  }
  if (key === "endpoint") {
    return rows.sort(
      (a, b) =>
        a.endpoint.localeCompare(b.endpoint) ||
        severityRank(a.severity) - severityRank(b.severity),
    );
  }
  if (key === "title") {
    return rows.sort((a, b) => a.title.localeCompare(b.title));
  }
  return rows.sort(
    (a, b) =>
      severityRank(a.severity) - severityRank(b.severity) ||
      byRisk(a, b) ||
      a.endpoint.localeCompare(b.endpoint),
  );
}

/**
 * Toggle a severity in a filter set.
 * @param {string[]} selected
 * @param {string} severity
 */
export function toggleSeverity(selected, severity) {
  return selected.includes(severity)
    ? selected.filter((item) => item !== severity)
    : [...selected, severity];
}

/**
 * Validate a target base URL the way the scanners need it: an absolute
 * http(s) URL.
 * @param {string} value
 * @returns {string|null} An error message, or null when valid.
 */
export function validateBaseUrl(value) {
  const trimmed = value.trim();
  if (trimmed === "") {
    return "Base URL is required.";
  }
  let parsed;
  try {
    parsed = new URL(trimmed);
  } catch {
    return "Enter an absolute URL, e.g. https://api.example.com";
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return "Only http:// and https:// targets are supported.";
  }
  return null;
}

/**
 * Validate a password against the registration schema
 * (min 8 characters, max 72 bytes because of bcrypt).
 * @param {string} value
 * @returns {string|null} An error message, or null when valid.
 */
export function validatePassword(value) {
  if (value.length < 8) {
    return "Password must be at least 8 characters.";
  }
  if (new TextEncoder().encode(value).length > 72) {
    return "Password must be at most 72 bytes.";
  }
  return null;
}

/**
 * Pretty-print a captured request/response body. Values that are not JSON are
 * returned unchanged so nothing is hidden from the analyst.
 * @param {string|null|undefined} raw
 */
export function formatEvidenceBody(raw) {
  if (raw === null || raw === undefined || raw === "") {
    return "";
  }
  const text = String(raw);
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

/**
 * Describe one entry of a FastAPI validation error list.
 * @param {unknown} issue
 * @returns {string}
 */
function describeValidationIssue(issue) {
  if (typeof issue === "string") {
    return issue;
  }
  if (issue === null || typeof issue !== "object") {
    return "";
  }
  const message = typeof issue.msg === "string" ? issue.msg : "";
  if (message === "") {
    return "";
  }
  const location = Array.isArray(issue.loc)
    ? issue.loc.filter((part) => typeof part === "string" && part !== "body")
    : [];
  return location.length === 0 ? message : `${location.join(".")}: ${message}`;
}

/**
 * Turn an error response body into a message an analyst can act on.
 *
 * FastAPI returns `{"detail": "..."}` for application errors but
 * `{"detail": [{"loc": [...], "msg": "..."}]}` for request-validation
 * failures. Showing only the status code for the latter hid the real problem
 * (for example a rejected base URL or password).
 *
 * @param {unknown} body Parsed JSON body, if the response had one.
 * @param {number} status HTTP status code.
 * @returns {string}
 */
export function formatApiErrorBody(body, status) {
  const detail =
    body !== null && typeof body === "object" ? body.detail : undefined;
  if (typeof detail === "string" && detail.trim() !== "") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map(describeValidationIssue)
      .filter((message) => message !== "");
    if (messages.length > 0) {
      return messages.join("; ");
    }
  }
  return `Request failed with status ${status}`;
}
