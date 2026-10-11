/**
 * Unit tests for the pure domain helpers that drive the UI (severity and
 * status vocabulary, OWASP mapping, risk bands, finding filtering/sorting and
 * input validation).
 *
 * Run with `npm test` from frontend/ — no test framework or bundler needed.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  categoryBreakdown,
  categoryBreakdownFromCounts,
  confidenceLabel,
  filterFindings,
  formatApiErrorBody,
  formatEvidenceBody,
  isScanActive,
  isScanFinished,
  owaspLabel,
  owaspShort,
  riskBand,
  severityBreakdown,
  severityColor,
  severityLabel,
  severityRank,
  sortFindings,
  statusLabel,
  summarizeFindings,
  toggleSeverity,
  validateBaseUrl,
  validatePassword,
} from "../src/lib/domain.js";

function finding(overrides = {}) {
  return {
    id: 1,
    title: "Missing security header",
    description: "Strict-Transport-Security is not set.",
    severity: "medium",
    endpoint: "GET /api/v1/orders",
    owasp_category: "api8:2023",
    confidence: "high",
    risk_score: 6.0,
    ...overrides,
  };
}

test("severityRank orders critical first and pushes unknown values last", () => {
  assert.ok(severityRank("critical") < severityRank("high"));
  assert.ok(severityRank("high") < severityRank("medium"));
  assert.ok(severityRank("medium") < severityRank("low"));
  assert.ok(severityRank("low") < severityRank("info"));
  assert.equal(severityRank("nonsense"), 5);
});

test("severity and status labels fall back to the raw value", () => {
  assert.equal(severityLabel("critical"), "Critical");
  assert.equal(severityLabel("unknown"), "unknown");
  assert.equal(statusLabel("completed_with_errors"), "Completed with errors");
  assert.equal(statusLabel("queued"), "Queued");
});

test("severity colours fall back to the info colour", () => {
  assert.equal(severityColor("critical"), "#b91c1c");
  assert.equal(severityColor("nonsense"), "#475569");
});

test("scan status helpers split active and finished states", () => {
  assert.equal(isScanActive("queued"), true);
  assert.equal(isScanActive("running"), true);
  assert.equal(isScanActive("completed"), false);
  assert.equal(isScanFinished("completed"), true);
  assert.equal(isScanFinished("completed_with_errors"), true);
  assert.equal(isScanFinished("failed"), true);
  assert.equal(isScanFinished("running"), false);
});

test("OWASP helpers expand known codes and degrade gracefully", () => {
  assert.equal(owaspShort("api1:2023"), "API1");
  assert.equal(owaspShort("api10:2023"), "API10");
  assert.equal(
    owaspLabel("api1:2023"),
    "API1:2023 Broken Object Level Authorization",
  );
  assert.equal(
    owaspLabel("api10:2023"),
    "API10:2023 Unsafe Consumption of APIs",
  );
  // Unknown codes must not throw: they are shown verbatim.
  assert.equal(owaspLabel("api99:2023"), "api99:2023");
  assert.equal(owaspShort("api99:2023"), "API99");
});

test("risk bands match the backend boundaries (4/6/8 inclusive)", () => {
  assert.equal(riskBand(10), "critical");
  assert.equal(riskBand(8), "critical");
  assert.equal(riskBand(7.9), "high");
  assert.equal(riskBand(6), "high");
  assert.equal(riskBand(5.9), "medium");
  assert.equal(riskBand(4), "medium");
  assert.equal(riskBand(3.9), "low");
  assert.equal(riskBand(0), "low");
});

test("confidenceLabel is human readable", () => {
  assert.equal(confidenceLabel("high"), "High confidence");
  assert.equal(confidenceLabel("low"), "Low confidence");
  assert.equal(confidenceLabel("experimental"), "experimental");
});

test("summarizeFindings counts each severity and the total", () => {
  const summary = summarizeFindings([
    finding({ severity: "critical" }),
    finding({ severity: "high" }),
    finding({ severity: "high" }),
    finding({ severity: "info" }),
  ]);
  assert.deepEqual(summary, {
    critical: 1,
    high: 2,
    medium: 0,
    low: 0,
    info: 1,
    total: 4,
  });
});

test("severityBreakdown keeps a stable scale including empty severities", () => {
  const rows = severityBreakdown([finding({ severity: "critical" })]);
  assert.deepEqual(
    rows.map((row) => [row.severity, row.count]),
    [
      ["critical", 1],
      ["high", 0],
      ["medium", 0],
      ["low", 0],
      ["info", 0],
    ],
  );
});

test("categoryBreakdown groups by OWASP category in API1..API10 order", () => {
  const rows = categoryBreakdown([
    finding({ owasp_category: "api10:2023" }),
    finding({ owasp_category: "api1:2023" }),
    finding({ owasp_category: "api1:2023" }),
  ]);
  assert.deepEqual(
    rows.map((row) => [row.code, row.count]),
    [
      ["api1:2023", 2],
      ["api10:2023", 1],
    ],
  );
  assert.equal(rows[0].label, "API1:2023 Broken Object Level Authorization");
});

test("categoryBreakdownFromCounts renders dashboard aggregates", () => {
  const rows = categoryBreakdownFromCounts({ "api8:2023": 5 });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].short, "API8");
  assert.equal(rows[0].count, 5);
});

test("filterFindings searches text and respects severity/category filters", () => {
  const findings = [
    finding({ title: "Permissive CORS", severity: "high", owasp_category: "api8:2023" }),
    finding({ title: "Weak JWT secret", severity: "critical", owasp_category: "api2:2023" }),
    finding({ title: "SQL error leaked", severity: "medium", owasp_category: "api10:2023", endpoint: "POST /api/v1/search" }),
  ];

  assert.equal(filterFindings(findings).length, 3);
  // Empty severity list means "every severity".
  assert.equal(filterFindings(findings, { severities: [] }).length, 3);
  assert.equal(filterFindings(findings, { severities: ["critical"] }).length, 1);
  assert.equal(
    filterFindings(findings, { category: "api8:2023" }).length,
    1,
  );
  assert.equal(filterFindings(findings, { query: "cors" }).length, 1);
  assert.equal(filterFindings(findings, { query: "POST /api" }).length, 1);
  assert.equal(filterFindings(findings, { query: "API2" }).length, 1);
  assert.equal(
    filterFindings(findings, {
      query: "jwt",
      severities: ["high"],
    }).length,
    0,
  );
});

test("sortFindings orders by severity then risk, and by other keys", () => {
  const findings = [
    finding({ id: 1, severity: "low", risk_score: 3, endpoint: "GET /b" }),
    finding({ id: 2, severity: "critical", risk_score: 7.5, endpoint: "GET /c" }),
    finding({ id: 3, severity: "critical", risk_score: 10, endpoint: "GET /a" }),
  ];

  assert.deepEqual(
    sortFindings(findings).map((row) => row.id),
    [3, 2, 1],
  );
  assert.deepEqual(
    sortFindings(findings, "risk").map((row) => row.id),
    [3, 2, 1],
  );
  assert.deepEqual(
    sortFindings(findings, "endpoint").map((row) => row.id),
    [3, 1, 2],
  );
  assert.deepEqual(
    sortFindings(findings, "title").map((row) => row.id),
    [1, 2, 3],
  );
  // The input array must not be reordered in place.
  assert.deepEqual(
    findings.map((row) => row.id),
    [1, 2, 3],
  );
});

test("toggleSeverity adds and removes a severity", () => {
  assert.deepEqual(toggleSeverity([], "high"), ["high"]);
  assert.deepEqual(toggleSeverity(["high"], "high"), []);
  assert.deepEqual(toggleSeverity(["high"], "low"), ["high", "low"]);
});

test("validateBaseUrl accepts absolute http(s) URLs only", () => {
  assert.equal(validateBaseUrl("https://api.example.com"), null);
  assert.equal(validateBaseUrl("http://localhost:8000"), null);
  assert.equal(validateBaseUrl(""), "Base URL is required.");
  assert.equal(
    validateBaseUrl("api.example.com"),
    "Enter an absolute URL, e.g. https://api.example.com",
  );
  assert.equal(
    validateBaseUrl("ftp://api.example.com"),
    "Only http:// and https:// targets are supported.",
  );
});

test("validatePassword enforces the registration schema bounds", () => {
  assert.equal(validatePassword("short"), "Password must be at least 8 characters.");
  assert.equal(validatePassword("12345678"), null);
  assert.equal(validatePassword("a".repeat(72)), null);
  assert.equal(
    validatePassword("a".repeat(73)),
    "Password must be at most 72 bytes.",
  );
  // bcrypt's limit is bytes, not characters.
  assert.equal(
    validatePassword("é".repeat(37)),
    "Password must be at most 72 bytes.",
  );
});

test("formatEvidenceBody pretty-prints JSON and passes other text through", () => {
  assert.equal(
    formatEvidenceBody('{"a":1}'),
    '{\n  "a": 1\n}',
  );
  assert.equal(formatEvidenceBody("HTTP/1.1 500 Internal Server Error"), "HTTP/1.1 500 Internal Server Error");
  assert.equal(formatEvidenceBody(null), "");
  assert.equal(formatEvidenceBody(undefined), "");
  assert.equal(formatEvidenceBody(""), "");
});

test("formatApiErrorBody surfaces string and validation-array details", () => {
  assert.equal(
    formatApiErrorBody({ detail: "Project not found" }, 404),
    "Project not found",
  );

  // FastAPI validation errors carry a list of issues; the old client dropped
  // them and showed only "Request failed with status 422".
  assert.equal(
    formatApiErrorBody(
      { detail: [{ loc: ["body", "base_url"], msg: "must be a valid URL" }] },
      422,
    ),
    "base_url: must be a valid URL",
  );
  assert.equal(
    formatApiErrorBody(
      {
        detail: [
          { loc: ["body", "email"], msg: "value is not a valid email" },
          {
            loc: ["body", "password"],
            msg: "String should have at least 8 characters",
          },
        ],
      },
      422,
    ),
    "email: value is not a valid email; password: String should have at least 8 characters",
  );

  // Unrecognised shapes fall back to the status code instead of "undefined".
  assert.equal(formatApiErrorBody(null, 500), "Request failed with status 500");
  assert.equal(
    formatApiErrorBody({ detail: [] }, 400),
    "Request failed with status 400",
  );
  assert.equal(
    formatApiErrorBody({ detail: "   " }, 400),
    "Request failed with status 400",
  );
});
