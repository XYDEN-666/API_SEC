/**
 * Backend API client.
 *
 * The backend base URL comes from the VITE_API_BASE_URL environment variable
 * (see .env.example). Vite inlines it at dev/build time.
 *
 * The JWT is held in module memory only (never localStorage/sessionStorage)
 * and is attached to every authenticated request; a page reload therefore
 * requires signing in again, as designed.
 */

import { formatApiErrorBody } from "../lib/domain";

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface HealthResponse {
  status: string;
}

export interface User {
  id: number;
  email: string;
  role: string;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Project {
  id: number;
  name: string;
  owner_id: number;
  created_at: string;
}

export interface Target {
  id: number;
  project_id: number;
  base_url: string;
  name: string;
}

export interface EndpointParameter {
  name?: string;
  in?: string;
  required?: boolean;
  description?: string;
}

export interface Endpoint {
  id: number;
  target_id: number;
  path: string;
  method: string;
  parameters: EndpointParameter[] | null;
}

export interface Credential {
  id: number;
  target_id: number;
  identity_name: string;
  auth_type: string;
  masked_value: string;
}

export interface AuthorizationRecord {
  id: number;
  project_id: number;
  description: string;
  scope_notes: string | null;
}

export interface ImportOpenApiResult {
  message: string;
  openapi: string;
  title: string | null;
  version: string | null;
  paths_count: number;
  endpoints_count: number;
}

export interface Scan {
  id: number;
  target_id: number;
  status: string;
  started_at: string;
  finished_at: string | null;
}

export interface ReportEvidence {
  evidence_id: number;
  scanner_name: string;
  request_data: string | null;
  response_data: string | null;
  timestamp: string | null;
}

export interface ReportFinding {
  id: number;
  scan_id: number;
  title: string;
  description: string;
  severity: string;
  endpoint: string;
  evidence_id: number | null;
  owasp_category: string;
  confidence: string;
  evidence_text: string | null;
  created_at: string;
  risk_score: number;
  risk_label: string;
  evidence: ReportEvidence | null;
}

export interface ReportSummary {
  info: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
  total: number;
}

export interface ReportMetadata {
  scan_id: number;
  target_id: number;
  target_name: string;
  base_url: string;
  project_id: number;
  project_name: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  generated_at: string;
}

export interface ReportData {
  metadata: ReportMetadata;
  summary: ReportSummary;
  findings: ReportFinding[];
}

export interface TopFinding {
  title: string;
  severity: string;
}

export interface RecentScan {
  id: number;
  target_id: number;
  target_name: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  top_finding: TopFinding | null;
}

export interface DashboardSummary {
  total_projects: number;
  total_targets: number;
  total_scans: number;
  /** Every finding row; scanners report once per endpoint examined. */
  total_findings: number;
  /** The same findings collapsed to one row per (issue, location). */
  total_distinct_issues: number;
  findings_by_severity: Record<string, number>;
  findings_by_category: Record<string, number>;
  recent_scans: RecentScan[];
}

/** Error carrying the HTTP status so callers can special-case 401/404/409. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let accessToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/**
 * Register a callback invoked when the API rejects a request with 401, so the
 * app can drop the session and return to the login screen.
 */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    return formatApiErrorBody(body, response.status);
  } catch {
    // Non-JSON error body; fall through to the generic message.
  }
  return `Request failed with status ${response.status}`;
}

async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken !== null) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(
      `Cannot reach the API at ${API_BASE_URL}. Is the backend running?`,
      0,
    );
  }

  if (!response.ok) {
    const message = await readErrorMessage(response);
    if (response.status === 401 && onUnauthorized !== null) {
      onUnauthorized();
    }
    throw new ApiError(message, response.status);
  }
  return response;
}

async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, options);
  return (await response.json()) as T;
}

/* ------------------------------- health ------------------------------- */

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new ApiError(
      `Health check failed with status ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as HealthResponse;
}

/* -------------------------------- auth -------------------------------- */

export function register(email: string, password: string): Promise<User> {
  return apiJson<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiJson<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(): Promise<User> {
  return apiJson<User>("/auth/me");
}

/* ------------------------------ projects ------------------------------ */

export function listProjects(): Promise<Project[]> {
  return apiJson<Project[]>("/projects");
}

export function createProject(name: string): Promise<Project> {
  return apiJson<Project>("/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function getProject(projectId: number): Promise<Project> {
  return apiJson<Project>(`/projects/${projectId}`);
}

export function updateProject(
  projectId: number,
  name: string,
): Promise<Project> {
  return apiJson<Project>(`/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export async function deleteProject(projectId: number): Promise<void> {
  await apiFetch(`/projects/${projectId}`, { method: "DELETE" });
}

/* ------------------------------- targets ------------------------------ */

export function listTargets(projectId: number): Promise<Target[]> {
  return apiJson<Target[]>(`/projects/${projectId}/targets`);
}

export function createTarget(
  projectId: number,
  name: string,
  baseUrl: string,
): Promise<Target> {
  return apiJson<Target>(`/projects/${projectId}/targets`, {
    method: "POST",
    body: JSON.stringify({ name, base_url: baseUrl }),
  });
}

export function getTarget(targetId: number): Promise<Target> {
  return apiJson<Target>(`/targets/${targetId}`);
}

export function updateTarget(
  targetId: number,
  name: string,
  baseUrl: string,
): Promise<Target> {
  return apiJson<Target>(`/targets/${targetId}`, {
    method: "PUT",
    body: JSON.stringify({ name, base_url: baseUrl }),
  });
}

export async function deleteTarget(targetId: number): Promise<void> {
  await apiFetch(`/targets/${targetId}`, { method: "DELETE" });
}

export function importOpenApi(
  targetId: number,
  file: File,
): Promise<ImportOpenApiResult> {
  const form = new FormData();
  form.append("file", file);
  return apiJson<ImportOpenApiResult>(`/targets/${targetId}/import-openapi`, {
    method: "POST",
    body: form,
  });
}

export function listEndpoints(targetId: number): Promise<Endpoint[]> {
  return apiJson<Endpoint[]>(`/targets/${targetId}/endpoints`);
}

/* ----------------------------- credentials ---------------------------- */

export function listCredentials(targetId: number): Promise<Credential[]> {
  return apiJson<Credential[]>(`/targets/${targetId}/credentials`);
}

export function createCredential(
  targetId: number,
  identityName: string,
  authType: string,
  value: string,
): Promise<Credential> {
  return apiJson<Credential>(`/targets/${targetId}/credentials`, {
    method: "POST",
    body: JSON.stringify({
      identity_name: identityName,
      auth_type: authType,
      value,
    }),
  });
}

export async function deleteCredential(
  targetId: number,
  credentialId: number,
): Promise<void> {
  await apiFetch(`/targets/${targetId}/credentials/${credentialId}`, {
    method: "DELETE",
  });
}

/* ------------------------ authorization records ----------------------- */

export function listAuthorizationRecords(
  projectId: number,
): Promise<AuthorizationRecord[]> {
  return apiJson<AuthorizationRecord[]>(
    `/projects/${projectId}/authorization-records`,
  );
}

export function createAuthorizationRecord(
  projectId: number,
  description: string,
  scopeNotes: string | null,
): Promise<AuthorizationRecord> {
  return apiJson<AuthorizationRecord>(
    `/projects/${projectId}/authorization-records`,
    {
      method: "POST",
      body: JSON.stringify({ description, scope_notes: scopeNotes }),
    },
  );
}

export function updateAuthorizationRecord(
  recordId: number,
  description: string,
  scopeNotes: string | null,
): Promise<AuthorizationRecord> {
  return apiJson<AuthorizationRecord>(`/authorization-records/${recordId}`, {
    method: "PUT",
    body: JSON.stringify({ description, scope_notes: scopeNotes }),
  });
}

export async function deleteAuthorizationRecord(
  recordId: number,
): Promise<void> {
  await apiFetch(`/authorization-records/${recordId}`, { method: "DELETE" });
}

/* -------------------------------- scans ------------------------------- */

export function listScans(targetId: number): Promise<Scan[]> {
  return apiJson<Scan[]>(`/targets/${targetId}/scans`);
}

export function startScan(
  targetId: number,
): Promise<{ scan_id: number; status: string }> {
  return apiJson<{ scan_id: number; status: string }>(
    `/targets/${targetId}/scans`,
    { method: "POST" },
  );
}

export function listScanFindings(scanId: number): Promise<ReportFinding[]> {
  return apiJson<ReportFinding[]>(`/scans/${scanId}/findings`);
}

/* ------------------------------- reports ------------------------------ */

export function getReport(scanId: number): Promise<ReportData> {
  return apiJson<ReportData>(`/scans/${scanId}/report.json`);
}

export async function downloadReport(
  scanId: number,
  format: "html" | "pdf" | "json",
): Promise<void> {
  const response = await apiFetch(`/scans/${scanId}/report.${format}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `scan-${scanId}-report.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

/* ------------------------------ dashboard ----------------------------- */

export function getDashboardSummary(): Promise<DashboardSummary> {
  return apiJson<DashboardSummary>("/dashboard/summary");
}
