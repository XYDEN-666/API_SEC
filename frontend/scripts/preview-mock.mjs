/**
 * One-command UI preview.
 *
 * Starts the fixture API (scripts/mock-api.mjs) and the Vite dev server with
 * VITE_API_BASE_URL pointing at it, so the interface can be reviewed without
 * PostgreSQL, Redis, Celery or Docker — and without needing per-shell syntax
 * to set an environment variable.
 *
 *   npm run preview:mock
 *
 * Both processes run as Node children (no shell), so this behaves identically
 * in cmd.exe, PowerShell, Git Bash and CI. Ctrl+C stops both.
 *
 * Ports: fixture API :8001 (MOCK_API_PORT), dev server :5173 (VITE_PORT).
 */

import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");

const API_PORT = process.env.MOCK_API_PORT ?? "8001";
const VITE_PORT = process.env.VITE_PORT ?? "5173";
const API_URL = process.env.VITE_API_BASE_URL ?? `http://localhost:${API_PORT}`;

const children = [];
let shuttingDown = false;

function launch(label, args, env = {}) {
  const child = spawn(process.execPath, args, {
    cwd: root,
    stdio: "inherit",
    env: { ...process.env, ...env },
  });
  children.push(child);
  child.on("exit", (code) => {
    if (shuttingDown) {
      return;
    }
    console.log(`\n[preview] ${label} exited (code ${code ?? 0}); stopping the rest.`);
    shutdown(code ?? 0);
  });
  child.on("error", (error) => {
    console.error(`[preview] could not start ${label}: ${error.message}`);
    shutdown(1);
  });
  return child;
}

function shutdown(code) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;
  for (const child of children) {
    if (child.exitCode === null) {
      child.kill();
    }
  }
  setTimeout(() => process.exit(code), 300).unref();
}

process.on("SIGINT", () => {
  console.log("\n[preview] stopping…");
  shutdown(0);
});
process.on("SIGTERM", () => shutdown(0));

console.log(`[preview] fixture API  → http://localhost:${API_PORT}`);
console.log(`[preview] frontend     → http://localhost:${VITE_PORT}`);
console.log("[preview] sign in with any email and an 8+ character password\n");

launch("fixture API", [join(root, "scripts", "mock-api.mjs")]);
launch("vite", [join(root, "node_modules", "vite", "bin", "vite.js"), "--port", VITE_PORT], {
  VITE_API_BASE_URL: API_URL,
});
