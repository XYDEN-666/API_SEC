/**
 * Backend API client.
 *
 * The backend base URL comes from the VITE_API_BASE_URL environment
 * variable (see .env.example). Vite inlines it at dev/build time.
 *
 * The JWT is held in module memory only (never localStorage/sessionStorage)
 * and is attached to every authenticated request.
 */
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

export interface Endpoint {
  id: number;
  target_id: number;
  path: string;
  method: string;
  parameters: unknown[] | null;
}

export interface Credential {
  id: number;
  target_id: number;
  identity_name: string;
  auth_type: string;
  masked_value: string;
}

export interface ImportOpenApiResult {
  message: string;
  openapi: string;
  title: string | null;
  version: string | null;
  paths_count: number;
  endpoints_count: number;
}

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
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

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Non-JSON error body; keep the generic message.
    }
    throw new Error(message);
  }
  return response;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}

export async function register(
  email: string,
  password: string,
): Promise<User> {
  const response = await apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return (await response.json()) as User;
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return (await response.json()) as LoginResponse;
}

export async function getMe(): Promise<User> {
  const response = await apiFetch("/auth/me");
  return (await response.json()) as User;
}

export async function listProjects(): Promise<Project[]> {
  const response = await apiFetch("/projects");
  return (await response.json()) as Project[];
}

export async function createProject(name: string): Promise<Project> {
  const response = await apiFetch("/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  return (await response.json()) as Project;
}

export async function getProject(projectId: number): Promise<Project> {
  const response = await apiFetch(`/projects/${projectId}`);
  return (await response.json()) as Project;
}

export async function listTargets(projectId: number): Promise<Target[]> {
  const response = await apiFetch(`/projects/${projectId}/targets`);
  return (await response.json()) as Target[];
}

export async function createTarget(
  projectId: number,
  name: string,
  baseUrl: string,
): Promise<Target> {
  const response = await apiFetch(`/projects/${projectId}/targets`, {
    method: "POST",
    body: JSON.stringify({ name, base_url: baseUrl }),
  });
  return (await response.json()) as Target;
}

export async function importOpenApi(
  targetId: number,
  file: File,
): Promise<ImportOpenApiResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await apiFetch(`/targets/${targetId}/import-openapi`, {
    method: "POST",
    body: form,
  });
  return (await response.json()) as ImportOpenApiResult;
}

export async function listEndpoints(targetId: number): Promise<Endpoint[]> {
  const response = await apiFetch(`/targets/${targetId}/endpoints`);
  return (await response.json()) as Endpoint[];
}

export async function listCredentials(
  targetId: number,
): Promise<Credential[]> {
  const response = await apiFetch(`/targets/${targetId}/credentials`);
  return (await response.json()) as Credential[];
}

export async function createCredential(
  targetId: number,
  identityName: string,
  authType: string,
  value: string,
): Promise<Credential> {
  const response = await apiFetch(`/targets/${targetId}/credentials`, {
    method: "POST",
    body: JSON.stringify({
      identity_name: identityName,
      auth_type: authType,
      value,
    }),
  });
  return (await response.json()) as Credential;
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

export async function listScans(targetId: number): Promise<Scan[]> {
  const response = await apiFetch(`/targets/${targetId}/scans`);
  return (await response.json()) as Scan[];
}

export async function startScan(
  targetId: number,
): Promise<{ scan_id: string; status: string }> {
  const response = await apiFetch(`/targets/${targetId}/scans`, {
    method: "POST",
  });
  return (await response.json()) as { scan_id: string; status: string };
}

export async function getReport(scanId: number): Promise<ReportData> {
  const response = await apiFetch(`/scans/${scanId}/report.json`);
  return (await response.json()) as ReportData;
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
