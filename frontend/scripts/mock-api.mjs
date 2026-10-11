/**
 * Development-only fixture API.
 *
 * Serves a small in-memory version of the APIShield API so the UI can be
 * previewed and smoke-tested without PostgreSQL, Redis, Celery or Docker.
 * It is NOT part of the product and must never be used as a real backend:
 * there is no encryption, no persistence and every token is accepted.
 *
 *   node scripts/mock-api.mjs            # listens on http://localhost:8001
 *   VITE_API_BASE_URL=http://localhost:8001 npm run dev
 */

import { createServer } from "node:http";

const PORT = Number(process.env.MOCK_API_PORT ?? 8001);
const FALLBACK_ORIGIN = process.env.MOCK_API_ORIGIN ?? "http://localhost:5173";

/** Echo back any loopback origin so both localhost and 127.0.0.1 work. */
function allowedOrigin(requestOrigin) {
  if (
    typeof requestOrigin === "string" &&
    /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(requestOrigin)
  ) {
    return requestOrigin;
  }
  return FALLBACK_ORIGIN;
}

const SEVERITY_WEIGHT = { info: 2, low: 4, medium: 6, high: 8, critical: 10 };
const CONFIDENCE_WEIGHT = { low: 0.5, medium: 0.75, high: 1 };
const CATEGORY_FOR_SCANNER = {
  idor_bola: "api1:2023",
  jwt: "api2:2023",
  headers: "api8:2023",
  cors: "api8:2023",
  http_methods: "api8:2023",
  sqli_indicators: "api10:2023",
};

function riskScore(severity, confidence) {
  return Math.round(SEVERITY_WEIGHT[severity] * CONFIDENCE_WEIGHT[confidence] * 10) / 10;
}

function riskLabel(score) {
  if (score >= 8) return "Critical";
  if (score >= 6) return "High";
  if (score >= 4) return "Medium";
  return "Low";
}

/* ----------------------------- fixture data ---------------------------- */

const now = Date.now();
const iso = (offsetMs = 0) => new Date(now + offsetMs).toISOString();

const db = {
  user: {
    id: 1,
    email: "analyst@example.com",
    role: "member",
    created_at: iso(-1000 * 60 * 60 * 24 * 30),
  },
  projects: [
    {
      id: 1,
      name: "Checkout API — staging",
      owner_id: 1,
      created_at: iso(-1000 * 60 * 60 * 24 * 12),
    },
    {
      id: 2,
      name: "Partner catalogue",
      owner_id: 1,
      created_at: iso(-1000 * 60 * 60 * 24 * 4),
    },
  ],
  targets: [
    {
      id: 1,
      project_id: 1,
      name: "Payments API (staging)",
      base_url: "https://pay.staging.example.com",
    },
    {
      id: 2,
      project_id: 1,
      name: "Orders API (staging)",
      base_url: "https://orders.staging.example.com",
    },
    {
      id: 3,
      project_id: 2,
      name: "Catalogue API",
      base_url: "https://catalog.partner.example.com",
    },
  ],
  authorizationRecords: [
    {
      id: 1,
      project_id: 1,
      description: "Authorised by the payments platform team, ticket SEC-4821",
      scope_notes:
        "Testing limited to /api/v1 between 18:00 and 22:00 IST. No destructive methods on production data.",
    },
  ],
  endpoints: [
    { id: 1, target_id: 1, path: "/api/v1/orders", method: "GET", parameters: [{ name: "status", in: "query" }, { name: "limit", in: "query" }] },
    { id: 2, target_id: 1, path: "/api/v1/orders", method: "POST", parameters: null },
    { id: 3, target_id: 1, path: "/api/v1/orders/{orderId}", method: "GET", parameters: [{ name: "orderId", in: "path", required: true }] },
    { id: 4, target_id: 1, path: "/api/v1/orders/{orderId}", method: "DELETE", parameters: [{ name: "orderId", in: "path", required: true }] },
    { id: 5, target_id: 1, path: "/api/v1/users/{userId}/profile", method: "GET", parameters: [{ name: "userId", in: "path", required: true }] },
    { id: 6, target_id: 1, path: "/api/v1/auth/token", method: "POST", parameters: null },
    { id: 7, target_id: 1, path: "/api/v1/products", method: "GET", parameters: [{ name: "cursor", in: "query" }] },
    { id: 8, target_id: 1, path: "/api/v1/products/{productId}", method: "PATCH", parameters: [{ name: "productId", in: "path", required: true }] },
    { id: 9, target_id: 3, path: "/v2/items", method: "GET", parameters: null },
  ],
  credentials: [
    { id: 1, target_id: 1, identity_name: "tenant-a", auth_type: "bearer", masked_value: "••••••••" },
    { id: 2, target_id: 1, identity_name: "tenant-b (low privilege)", auth_type: "api_key", masked_value: "••••••••" },
  ],
  scans: [],
  reports: new Map(),
  sequences: { project: 2, target: 3, record: 1, endpoint: 9, credential: 2, finding: 100, scan: 0 },
};

const FINDING_TEMPLATES = [
  {
    scanner: "idor_bola",
    title: "Object readable by a lower-privileged identity",
    description:
      "Replaying GET /api/v1/orders/{orderId} with the tenant-b credential returned the same object as tenant-a, indicating broken object level authorization.",
    endpoint: "GET /api/v1/orders/{orderId}",
    severity: "critical",
    confidence: "high",
    request_data:
      '{"method":"GET","url":"https://pay.staging.example.com/api/v1/orders/1042","headers":{"Authorization":"Bearer <tenant-b>"}}',
    response_data:
      '{"status":200,"body":{"orderId":1042,"customerId":"cus_88","total":189.5}}',
  },
  {
    scanner: "jwt",
    title: "JWT accepted without an expiry claim",
    description:
      "The token issued by POST /api/v1/auth/token contains no exp claim, so a stolen token stays valid indefinitely.",
    endpoint: "POST /api/v1/auth/token",
    severity: "high",
    confidence: "high",
    request_data: '{"method":"POST","url":"https://pay.staging.example.com/api/v1/auth/token"}',
    response_data:
      '{"status":200,"body":{"access_token":"eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZW5hbnQtYSJ9"}}',
  },
  {
    scanner: "headers",
    title: "Missing Strict-Transport-Security header",
    description:
      "Responses do not set Strict-Transport-Security, so browsers may fall back to plain HTTP on subsequent requests.",
    endpoint: "GET /api/v1/orders",
    severity: "medium",
    confidence: "high",
    request_data: '{"method":"GET","url":"https://pay.staging.example.com/api/v1/orders"}',
    response_data: '{"status":200,"headers":{"Content-Type":"application/json"}}',
  },
  {
    scanner: "cors",
    title: "Overly permissive CORS policy",
    description:
      "Access-Control-Allow-Origin reflects the request origin and Access-Control-Allow-Credentials is true, allowing any site to read authenticated responses.",
    endpoint: "GET /api/v1/products",
    severity: "high",
    confidence: "medium",
    request_data: '{"method":"GET","url":"https://pay.staging.example.com/api/v1/products","headers":{"Origin":"https://attacker.example"}}',
    response_data:
      '{"status":200,"headers":{"Access-Control-Allow-Origin":"https://attacker.example","Access-Control-Allow-Credentials":"true"}}',
  },
  {
    scanner: "sqli_indicators",
    title: "SQL error returned for a crafted query parameter",
    description:
      "A single quote in the status query parameter produced a database error message in the response, which indicates unparameterised SQL.",
    endpoint: "GET /api/v1/orders",
    severity: "high",
    confidence: "medium",
    request_data: '{"method":"GET","url":"https://pay.staging.example.com/api/v1/orders?status=paid%27"}',
    response_data:
      '{"status":500,"body":{"error":"syntax error at or near \\"\\""}}',
  },
  {
    scanner: "http_methods",
    title: "Unexpected DELETE method enabled",
    description:
      "OPTIONS advertised DELETE on a collection endpoint that the specification only documents as readable.",
    endpoint: "DELETE /api/v1/orders/{orderId}",
    severity: "info",
    confidence: "high",
    request_data: '{"method":"OPTIONS","url":"https://pay.staging.example.com/api/v1/orders"}',
    response_data: '{"status":204,"headers":{"Allow":"GET,POST,DELETE,OPTIONS"}}',
  },
];

function buildFindings(scanId, templateCount) {
  return FINDING_TEMPLATES.slice(0, templateCount).map((template) => {
    const score = riskScore(template.severity, template.confidence);
    db.sequences.finding += 1;
    return {
      id: db.sequences.finding,
      scan_id: scanId,
      title: template.title,
      description: template.description,
      severity: template.severity,
      endpoint: template.endpoint,
      evidence_id: db.sequences.finding,
      owasp_category: CATEGORY_FOR_SCANNER[template.scanner],
      confidence: template.confidence,
      evidence_text:
        template.evidence ?? `Mock capture for ${template.endpoint}`,
      created_at: iso(-1000 * 60 * 5),
      risk_score: score,
      risk_label: riskLabel(score),
      evidence: {
        evidence_id: db.sequences.finding,
        scanner_name: template.scanner,
        request_data: template.request_data,
        response_data: template.response_data,
        timestamp: iso(-1000 * 60 * 5),
      },
    };
  });
}

function addScan({ targetId, status, startedOffset, finishedOffset, findings }) {
  db.sequences.scan += 1;
  const scan = {
    id: db.sequences.scan,
    target_id: targetId,
    status,
    started_at: iso(startedOffset),
    finished_at: finishedOffset === null ? null : iso(finishedOffset),
  };
  db.scans.push(scan);
  db.reports.set(scan.id, buildFindings(scan.id, findings));
  return scan;
}

addScan({ targetId: 1, status: "completed", startedOffset: -1000 * 60 * 60 * 5, finishedOffset: -1000 * 60 * 60 * 5 + 18_400, findings: 6 });
addScan({ targetId: 1, status: "completed_with_errors", startedOffset: -1000 * 60 * 90, finishedOffset: -1000 * 60 * 90 + 9_600, findings: 4 });
addScan({ targetId: 3, status: "completed", startedOffset: -1000 * 60 * 30, finishedOffset: -1000 * 60 * 30 + 6_200, findings: 2 });

/* -------------------------------- helpers ------------------------------ */

function projectName(projectId) {
  return db.projects.find((project) => project.id === projectId)?.name ?? "Project";
}

function reportFor(scanId) {
  const scan = db.scans.find((item) => item.id === scanId);
  if (scan === undefined) {
    return null;
  }
  const target = db.targets.find((item) => item.id === scan.target_id);
  const findings = db.reports.get(scanId) ?? [];
  const summary = { critical: 0, high: 0, medium: 0, low: 0, info: 0, total: findings.length };
  for (const finding of findings) {
    summary[finding.severity] += 1;
  }
  return {
    metadata: {
      scan_id: scan.id,
      target_id: scan.target_id,
      target_name: target?.name ?? "Target",
      base_url: target?.base_url ?? "",
      project_id: target?.project_id ?? 1,
      project_name: projectName(target?.project_id ?? 1),
      status: scan.status,
      started_at: scan.started_at,
      finished_at: scan.finished_at,
      generated_at: iso(),
    },
    summary,
    findings,
  };
}

function dashboardSummary() {
  const findings = db.scans.flatMap((scan) => db.reports.get(scan.id) ?? []);
  const bySeverity = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  const byCategory = {};
  for (const finding of findings) {
    bySeverity[finding.severity] = (bySeverity[finding.severity] ?? 0) + 1;
    byCategory[finding.owasp_category] = (byCategory[finding.owasp_category] ?? 0) + 1;
  }
  const recent = [...db.scans]
    .sort((a, b) => b.id - a.id)
    .slice(0, 6)
    .map((scan) => {
      const target = db.targets.find((item) => item.id === scan.target_id);
      const scanFindings = db.reports.get(scan.id) ?? [];
      const top = [...scanFindings].sort((a, b) => b.risk_score - a.risk_score)[0];
      return {
        id: scan.id,
        target_id: scan.target_id,
        target_name: target?.name ?? "Target",
        status: scan.status,
        started_at: scan.started_at,
        finished_at: scan.finished_at,
        top_finding: top === undefined ? null : { title: top.title, severity: top.severity },
      };
    });
  // Same collapse the backend performs: one row per (issue, location), with
  // any leading HTTP-method token stripped from the stored endpoint.
  const distinctIssues = new Set(
    findings.map(
      (finding) =>
        `${finding.title}|${String(finding.endpoint ?? "").replace(/^[A-Z]+ /, "")}`,
    ),
  ).size;
  return {
    total_projects: db.projects.length,
    total_targets: db.targets.length,
    total_scans: db.scans.length,
    total_findings: findings.length,
    total_distinct_issues: distinctIssues,
    findings_by_severity: bySeverity,
    findings_by_category: byCategory,
    recent_scans: recent,
  };
}

function runScan(targetId) {
  db.sequences.scan += 1;
  const scan = {
    id: db.sequences.scan,
    target_id: targetId,
    status: "queued",
    started_at: iso(),
    finished_at: null,
  };
  db.scans.push(scan);
  db.reports.set(scan.id, []);

  setTimeout(() => {
    scan.status = "running";
  }, 1500);
  setTimeout(() => {
    scan.status = "completed";
    scan.finished_at = iso();
    db.reports.set(scan.id, buildFindings(scan.id, 5));
  }, 6000);
  return scan;
}

/* -------------------------------- routing ------------------------------ */

const ROUTES = [
  ["GET", /^\/health$/, () => ({ status: "ok" })],
  ["POST", /^\/auth\/register$/, (_match, body) => ({ ...db.user, email: body.email ?? db.user.email })],
  ["POST", /^\/auth\/login$/, () => ({ access_token: "mock-token", token_type: "bearer" })],
  ["GET", /^\/auth\/me$/, () => db.user],
  ["GET", /^\/dashboard\/summary$/, () => dashboardSummary()],

  ["GET", /^\/projects$/, () => db.projects],
  ["POST", /^\/projects$/, (_match, body) => {
    db.sequences.project += 1;
    const project = { id: db.sequences.project, name: body.name, owner_id: 1, created_at: iso() };
    db.projects.push(project);
    return project;
  }],
  ["GET", /^\/projects\/(\d+)$/, (match) => db.projects.find((p) => p.id === Number(match[1])) ?? 404],
  ["PUT", /^\/projects\/(\d+)$/, (match, body) => {
    const project = db.projects.find((p) => p.id === Number(match[1]));
    if (project === undefined) return 404;
    project.name = body.name;
    return project;
  }],
  ["DELETE", /^\/projects\/(\d+)$/, (match) => {
    const id = Number(match[1]);
    db.projects = db.projects.filter((p) => p.id !== id);
    db.targets = db.targets.filter((t) => t.project_id !== id);
    db.authorizationRecords = db.authorizationRecords.filter((r) => r.project_id !== id);
    return 204;
  }],

  ["GET", /^\/projects\/(\d+)\/targets$/, (match) => db.targets.filter((t) => t.project_id === Number(match[1]))],
  ["POST", /^\/projects\/(\d+)\/targets$/, (match, body) => {
    db.sequences.target += 1;
    const target = {
      id: db.sequences.target,
      project_id: Number(match[1]),
      name: body.name,
      base_url: body.base_url,
    };
    db.targets.push(target);
    return target;
  }],

  ["GET", /^\/targets\/(\d+)$/, (match) => db.targets.find((t) => t.id === Number(match[1])) ?? 404],
  ["PUT", /^\/targets\/(\d+)$/, (match, body) => {
    const target = db.targets.find((t) => t.id === Number(match[1]));
    if (target === undefined) return 404;
    target.name = body.name;
    target.base_url = body.base_url;
    return target;
  }],
  ["DELETE", /^\/targets\/(\d+)$/, (match) => {
    const id = Number(match[1]);
    db.targets = db.targets.filter((t) => t.id !== id);
    return 204;
  }],
  ["GET", /^\/targets\/(\d+)\/endpoints$/, (match) => db.endpoints.filter((e) => e.target_id === Number(match[1]))],
  ["POST", /^\/targets\/(\d+)\/import-openapi$/, (match) => {
    const targetId = Number(match[1]);
    if (!db.endpoints.some((endpoint) => endpoint.target_id === targetId)) {
      db.sequences.endpoint += 3;
      for (const path of ["/v1/reports", "/v1/reports/{reportId}", "/v1/webhooks"]) {
        db.endpoints.push({
          id: db.sequences.endpoint,
          target_id: targetId,
          path,
          method: "GET",
          parameters: null,
        });
      }
    }
    return {
      message: "OpenAPI 3.x document imported successfully",
      openapi: "3.0.3",
      title: "Payments API",
      version: "1.4.0",
      paths_count: 7,
      endpoints_count: db.endpoints.filter((e) => e.target_id === targetId).length,
    };
  }],

  ["GET", /^\/targets\/(\d+)\/credentials$/, (match) => db.credentials.filter((c) => c.target_id === Number(match[1]))],
  ["POST", /^\/targets\/(\d+)\/credentials$/, (match, body) => {
    db.sequences.credential += 1;
    const credential = {
      id: db.sequences.credential,
      target_id: Number(match[1]),
      identity_name: body.identity_name,
      auth_type: body.auth_type,
      masked_value: "••••••••",
    };
    db.credentials.push(credential);
    return credential;
  }],
  ["DELETE", /^\/targets\/(\d+)\/credentials\/(\d+)$/, (match) => {
    db.credentials = db.credentials.filter((c) => c.id !== Number(match[2]));
    return 204;
  }],

  ["GET", /^\/targets\/(\d+)\/scans$/, (match) =>
    db.scans
      .filter((scan) => scan.target_id === Number(match[1]))
      .sort((a, b) => b.id - a.id),
  ],
  ["POST", /^\/targets\/(\d+)\/scans$/, (match) => {
    const scan = runScan(Number(match[1]));
    // A real scan id, exactly like the backend: the UI polls this id.
    return { scan_id: scan.id, status: "queued" };
  }],

  ["GET", /^\/scans\/(\d+)\/report\.json$/, (match) => reportFor(Number(match[1])) ?? 404],
  ["GET", /^\/scans\/(\d+)\/findings$/, (match) => (db.reports.get(Number(match[1])) ?? []).map(({ evidence, ...finding }) => finding)],

  ["GET", /^\/projects\/(\d+)\/authorization-records$/, (match) =>
    db.authorizationRecords.filter((r) => r.project_id === Number(match[1])),
  ],
  ["POST", /^\/projects\/(\d+)\/authorization-records$/, (match, body) => {
    db.sequences.record += 1;
    const record = {
      id: db.sequences.record,
      project_id: Number(match[1]),
      description: body.description,
      scope_notes: body.scope_notes ?? null,
    };
    db.authorizationRecords.push(record);
    return record;
  }],
  ["PUT", /^\/authorization-records\/(\d+)$/, (match, body) => {
    const record = db.authorizationRecords.find((r) => r.id === Number(match[1]));
    if (record === undefined) return 404;
    record.description = body.description;
    record.scope_notes = body.scope_notes ?? null;
    return record;
  }],
  ["DELETE", /^\/authorization-records\/(\d+)$/, (match) => {
    db.authorizationRecords = db.authorizationRecords.filter((r) => r.id !== Number(match[1]));
    return 204;
  }],
];

function send(res, status, payload, contentType = "application/json", origin) {
  const body =
    payload === null || payload === undefined
      ? ""
      : contentType === "application/json"
        ? JSON.stringify(payload)
        : String(payload);
  res.writeHead(status, {
    "Content-Type": contentType,
    "Content-Length": Buffer.byteLength(body),
    "Access-Control-Allow-Origin": allowedOrigin(origin),
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
  });
  res.end(body);
}

const server = createServer((req, res) => {
  if (req.method === "OPTIONS") {
    send(res, 204, null, "application/json", req.headers.origin);
    return;
  }

  const url = new URL(req.url ?? "/", `http://localhost:${PORT}`);
  const path = url.pathname;

  let raw = "";
  req.on("data", (chunk) => {
    raw += chunk;
  });
  req.on("end", () => {
    if (
      path !== "/health" &&
      path !== "/auth/login" &&
      path !== "/auth/register" &&
      req.headers.authorization === undefined
    ) {
      send(res, 401, { detail: "Not authenticated" }, "application/json", req.headers.origin);
      return;
    }

    let body = {};
    const isMultipart = (req.headers["content-type"] ?? "").includes("multipart/form-data");
    if (raw !== "" && !isMultipart) {
      try {
        body = JSON.parse(raw);
      } catch {
        body = {};
      }
    }

    for (const [method, pattern, handler] of ROUTES) {
      const match = pattern.exec(path);
      if (match === null || method !== req.method) {
        continue;
      }
      const result = handler(match, body, req);
      if (result === 204) {
        send(res, 204, null, "application/json", req.headers.origin);
        return;
      }
      if (result === 404) {
        send(res, 404, { detail: "Not found" }, "application/json", req.headers.origin);
        return;
      }
      send(
        res,
        method === "POST" && path === "/auth/register" ? 201 : 200,
        result,
        "application/json",
        req.headers.origin,
      );
      return;
    }

    if (/^\/scans\/\d+\/report\.(html|pdf)$/.test(path)) {
      send(
        res,
        200,
        `<html><body><h1>Mock report</h1><p>${path}</p></body></html>`,
        "text/html",
        req.headers.origin,
      );
      return;
    }

    send(
      res,
      404,
      { detail: `No mock route for ${req.method} ${path}` },
      "application/json",
      req.headers.origin,
    );
  });
});

server.listen(PORT, () => {
  console.log(`[mock-api] fixture API listening on http://localhost:${PORT}`);
  console.log(`[mock-api] sign in with any email and an 8+ character password`);
});

server.on("error", (error) => {
  if (error.code === "EADDRINUSE") {
    console.error(
      `[mock-api] port ${PORT} is already in use. Stop the other fixture ` +
        `instance or start this one on another port with MOCK_API_PORT=<port>.`,
    );
    process.exit(1);
  }
  throw error;
});
