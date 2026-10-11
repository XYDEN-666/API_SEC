import { request } from "node:http";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * The UI can talk to either the Docker backend (:8000) or the local fixture
 * API (:8001). Rather than requiring `VITE_API_BASE_URL` to be set with
 * shell-specific syntax, the dev server probes both at startup:
 *
 *   - an explicit VITE_API_BASE_URL always wins;
 *   - otherwise the first reachable backend is used;
 *   - if neither answers, the UI still starts and the client falls back to
 *     :8000, with a warning printed here.
 *
 * Production builds do not probe: the value is baked in at build time.
 */
const API_CANDIDATES = [
  { url: "http://localhost:8000", label: "backend (docker compose up)" },
  { url: "http://localhost:8001", label: "fixture API (npm run dev:mock)" },
];

function isReachable(url: string, timeoutMs = 700): Promise<boolean> {
  return new Promise((resolve) => {
    const probe = request(`${url}/health`, { method: "GET" }, (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    probe.setTimeout(timeoutMs, () => {
      probe.destroy();
      resolve(false);
    });
    probe.on("error", () => resolve(false));
    probe.end();
  });
}

export default defineConfig(async ({ command }) => {
  const configured = process.env.VITE_API_BASE_URL?.trim();
  const hasExplicit = configured !== undefined && configured !== "";
  let apiBase: string | null = hasExplicit ? (configured as string) : null;
  let source = "VITE_API_BASE_URL";

  if (apiBase === null && command === "serve") {
    for (const candidate of API_CANDIDATES) {
      if (await isReachable(candidate.url)) {
        apiBase = candidate.url;
        source = candidate.label;
        break;
      }
    }
  }

  // Vite reads VITE_* from process.env when it loads env values, so the value
  // resolved here reaches import.meta.env in the browser bundle.
  if (apiBase !== null && !hasExplicit) {
    process.env.VITE_API_BASE_URL = apiBase;
  }

  if (command === "serve") {
    if (apiBase !== null) {
      console.log(`\n  [apishield] API base URL → ${apiBase}  (${source})\n`);
    } else {
      console.log(
        "\n  [apishield] No backend found on :8000 or :8001.\n" +
          "  Start the stack (docker compose up) or the fixture (npm run preview:mock);\n" +
          "  the UI loads but API calls will fail.\n",
      );
    }
  }

  return {
    plugins: [react()],
    build: {
      rollupOptions: {
        output: {
          // Keep the charting library and the React runtime in their own
          // chunks: neither changes as often as application code.
          manualChunks: {
            react: ["react", "react-dom", "react-router-dom"],
            charts: ["recharts"],
          },
        },
      },
    },
    server: {
      host: true,
      port: 5173,
      allowedHosts: ["host.docker.internal"],
    },
  };
});
