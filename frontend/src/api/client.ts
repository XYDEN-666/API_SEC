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

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
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
