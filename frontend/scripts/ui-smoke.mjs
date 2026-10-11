/**
 * Headless UI smoke test.
 *
 * Drives the running frontend through Chrome's DevTools Protocol (pipe
 * transport, so no npm dependencies) and walks the real user journey:
 * sign in → dashboard → projects → project → authorization records → target →
 * endpoints → scans → scan results → finding detail → dark theme.
 *
 * Every step asserts on rendered output and screenshots are written to
 * $UI_SMOKE_OUT (default: <tmp>/apishield-ui-smoke). Any console error or
 * uncaught exception fails the run.
 *
 * Usage:
 *   npm run preview:mock                  # fixture API + dev server
 *   npm run test:ui                       # default target http://localhost:5173
 *
 * Env: UI_SMOKE_URL, UI_SMOKE_OUT, UI_SMOKE_CHROME, UI_SMOKE_EMAIL,
 *      UI_SMOKE_PASSWORD.
 */

import { spawn } from "node:child_process";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE_URL = process.env.UI_SMOKE_URL ?? "http://localhost:5173";
const OUT_DIR =
  process.env.UI_SMOKE_OUT ?? join(tmpdir(), "apishield-ui-smoke");
const EMAIL = process.env.UI_SMOKE_EMAIL ?? "analyst@example.com";
const PASSWORD = process.env.UI_SMOKE_PASSWORD ?? "correct-horse-battery";
const CHROME =
  process.env.UI_SMOKE_CHROME ??
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

/* ------------------------- DevTools pipe transport --------------------- */

class DevTools {
  constructor(process) {
    this.process = process;
    this.buffer = Buffer.alloc(0);
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Set();
    this.write = process.stdio[3];
    process.stdio[4].on("data", (chunk) => this.#onData(chunk));
  }

  #onData(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    let separator = this.buffer.indexOf(0);
    while (separator !== -1) {
      const raw = this.buffer.subarray(0, separator).toString("utf8");
      this.buffer = this.buffer.subarray(separator + 1);
      separator = this.buffer.indexOf(0);
      if (raw.trim() === "") {
        continue;
      }
      const message = JSON.parse(raw);
      if (message.id === undefined) {
        for (const listener of this.listeners) {
          listener(message);
        }
        continue;
      }
      const entry = this.pending.get(message.id);
      if (entry === undefined) {
        continue;
      }
      this.pending.delete(message.id);
      if (message.error !== undefined) {
        entry.reject(new Error(`${entry.method}: ${message.error.message}`));
      } else {
        entry.resolve(message.result);
      }
    }
  }

  send(method, params = {}, sessionId) {
    const id = this.nextId++;
    const entry = { method, resolve: null, reject: null };
    const promise = new Promise((resolve, reject) => {
      entry.resolve = resolve;
      entry.reject = reject;
    });
    this.pending.set(id, entry);
    const payload = sessionId === undefined
      ? { id, method, params }
      : { id, method, params, sessionId };
    this.write.write(`${JSON.stringify(payload)}\0`);
    // Never let a lost reply hang the run: fail with the method name instead.
    const timeout = new Promise((_resolve, reject) => {
      setTimeout(() => {
        if (this.pending.delete(id)) {
          reject(new Error(`DevTools timeout after 20000ms calling ${method}`));
        }
      }, 20_000);
    });
    return Promise.race([promise, timeout]);
  }

  onEvent(listener) {
    this.listeners.add(listener);
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/* ------------------------------ assertions ----------------------------- */

const results = [];
const consoleErrors = [];
let screenshots = 0;
let chromeProcess = null;

function check(name, condition, detail = "") {
  results.push({ name, ok: Boolean(condition), detail });
  const status = condition ? "PASS" : "FAIL";
  console.log(`  ${status}  ${name}${condition ? "" : `  ← ${detail}`}`);
}

/* -------------------------------- driver ------------------------------- */

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  const profile = await mkdtemp(join(tmpdir(), "apishield-chrome-"));

  const chrome = spawn(
    CHROME,
    [
      "--headless=new",
      "--no-sandbox",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-extensions",
      "--disable-dev-shm-usage",
      "--hide-scrollbars",
      `--user-data-dir=${profile}`,
      "--remote-debugging-pipe",
      "--window-size=1500,1040",
      "about:blank",
    ],
    { stdio: ["ignore", "pipe", "pipe", "pipe", "pipe"] },
  );
  chromeProcess = chrome;
  let chromeLog = "";
  chrome.stdout.on("data", (chunk) => {
    chromeLog += chunk.toString("utf8");
  });
  chrome.stderr.on("data", (chunk) => {
    chromeLog += chunk.toString("utf8");
  });
  chrome.on("exit", (code) => {
    if (code !== 0 && code !== null) {
      console.error(`chrome exited early (code=${code})`);
      console.error(chromeLog.slice(-2000));
    }
  });

  const devtools = new DevTools(chrome);
  if (devtools.write === null || devtools.write === undefined) {
    throw new Error("Chrome stdio[3] pipe was not created");
  }
  const { targetId } = await devtools.send("Target.createTarget", {
    url: "about:blank",
  });
  const { sessionId } = await devtools.send("Target.attachToTarget", {
    targetId,
    flatten: true,
  });
  const session = sessionId;

  devtools.onEvent((message) => {
    if (message.sessionId !== session) {
      return;
    }
    if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") {
      consoleErrors.push(
        message.params.args
          .map((arg) => arg.value ?? arg.description ?? arg.type)
          .join(" "),
      );
    }
    if (message.method === "Runtime.exceptionThrown") {
      consoleErrors.push(
        message.params.exceptionDetails.exception?.description ??
          message.params.exceptionDetails.text,
      );
    }
  });

  await devtools.send("Page.enable", {}, session);
  await devtools.send("Runtime.enable", {}, session);

  async function evaluate(expression) {
    const result = await devtools.send(
      "Runtime.evaluate",
      { expression, awaitPromise: true, returnByValue: true },
      session,
    );
    if (result.exceptionDetails !== undefined) {
      throw new Error(
        `evaluate failed: ${
          result.exceptionDetails.exception?.description ??
          result.exceptionDetails.text
        }`,
      );
    }
    return result.result.value;
  }

  async function waitFor(expression, label, timeoutMs = 15000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (await evaluate(expression)) {
        return;
      }
      await delay(150);
    }
    const visible = await evaluate("document.body.innerText.slice(0, 400)");
    throw new Error(
      `Timed out waiting for ${label}. Visible text: ${JSON.stringify(visible)}` +
        (consoleErrors.length > 0
          ? ` | console errors: ${consoleErrors.slice(0, 3).join(" | ")}`
          : ""),
    );
  }

  async function goto(url) {
    await devtools.send("Page.navigate", { url }, session);
    await waitFor("document.readyState === 'complete'", "page load");
  }

  async function clickSelector(expression, label) {
    const clicked = await evaluate(`(() => {
      const element = ${expression};
      if (!element) return false;
      element.click();
      return true;
    })()`);
    if (!clicked) {
      throw new Error(`Could not click ${label}`);
    }
  }

  async function shot(name) {
    await delay(250);
    const { data } = await devtools.send(
      "Page.captureScreenshot",
      { format: "png" },
      session,
    );
    screenshots += 1;
    const file = join(OUT_DIR, `${String(screenshots).padStart(2, "0")}-${name}.png`);
    await writeFile(file, Buffer.from(data, "base64"));
    return file;
  }

  const text = () => evaluate("document.body.innerText");
  const hasText = (value) =>
    `document.body.innerText.includes(${JSON.stringify(value)})`;

  /* ------------------------------ journey ----------------------------- */

  console.log(`\nAPIShield UI smoke test → ${BASE_URL}\n`);

  await goto(`${BASE_URL}/login`);
  await waitFor(hasText("Sign in"), "login form");
  check("login page renders the sign-in form", await evaluate(hasText("Sign in")));
  check(
    "login page shows the product hero",
    await evaluate(hasText("Find API security gaps before someone else does.")),
  );
  await shot("login");

  await evaluate(`(() => {
    const set = (selector, value) => {
      const element = document.querySelector(selector);
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
      setter.call(element, value);
      element.dispatchEvent(new Event("input", { bubbles: true }));
    };
    set('input[type="email"]', ${JSON.stringify(EMAIL)});
    set('input[type="password"]', ${JSON.stringify(PASSWORD)});
    return true;
  })()`);
  await clickSelector("document.querySelector('button[type=submit]')", "sign in");
  await waitFor("document.querySelector('.stat-card') !== null", "dashboard");
  check("sign-in lands on the dashboard", await evaluate(hasText("Dashboard")));
  check(
    "dashboard shows KPI cards",
    (await evaluate("document.querySelectorAll('.stat-card').length")) >= 4,
  );
  check(
    "dashboard charts severity breakdown",
    await evaluate(hasText("Findings by severity")),
  );
  check(
    "dashboard lists recent scans",
    await evaluate(hasText("Recent scans")),
  );
  await shot("dashboard");

  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => a.getAttribute('href') === '/projects')",
    "Projects nav link",
  );
  await waitFor(hasText("All projects"), "projects page");
  check(
    "projects page lists the seeded project",
    await evaluate(hasText("Checkout API — staging")),
  );
  await shot("projects");

  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => a.getAttribute('href') === '/projects/1')",
    "project row",
  );
  // Wait for the loaded target row, not just the "Targets" heading.
  await waitFor(hasText("Payments API (staging)"), "project detail targets");
  check("project detail lists targets", true);
  await shot("project-detail");

  await clickSelector(
    "[...document.querySelectorAll('button[role=tab]')].find((b) => b.textContent.includes('Authorization'))",
    "authorization tab",
  );
  await waitFor(hasText("Authorization records"), "authorization records");
  check(
    "authorization records are visible",
    await evaluate(hasText("ticket SEC-4821")),
  );
  await shot("authorization-records");

  // Back to the targets tab before following a target through.
  await clickSelector(
    "[...document.querySelectorAll('button[role=tab]')].find((b) => b.textContent.includes('Targets'))",
    "targets tab",
  );
  await waitFor(hasText("Payments API (staging)"), "targets tab");

  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => a.getAttribute('href') === '/targets/1')",
    "target link",
  );
  await waitFor(hasText("/api/v1/orders"), "target detail endpoints");
  check(
    "target detail lists imported endpoints",
    await evaluate(hasText("/api/v1/orders")),
  );
  check(
    "target detail summarises identities",
    await evaluate(hasText("Identities")),
  );
  await shot("target-detail");

  await clickSelector(
    "[...document.querySelectorAll('button[role=tab]')].find((b) => b.textContent.includes('Credentials'))",
    "credentials tab",
  );
  await waitFor(hasText("tenant-a"), "credentials");
  check(
    "credentials are listed masked",
    await evaluate(hasText("tenant-a")),
  );
  check(
    "secrets are never shown in clear",
    await evaluate("document.body.innerText.includes('••••••••')"),
  );
  await shot("credentials");

  await clickSelector(
    "[...document.querySelectorAll('button[role=tab]')].find((b) => b.textContent.includes('Scans'))",
    "scans tab",
  );
  await waitFor(
    "document.querySelectorAll('.table tbody tr').length > 0",
    "scan history rows",
  );
  check(
    "scan history lists completed scans",
    await evaluate(hasText("Completed")),
  );
  await shot("scans");

  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => (a.getAttribute('href') ?? '').startsWith('/targets/1/scans/1'))",
    "scan results link",
  );
  await waitFor(
    "document.querySelectorAll('.finding-card').length > 0",
    "scan findings",
  );
  check("scan results render a summary", await evaluate(hasText("Summary")));
  check(
    "findings render with OWASP categories",
    await evaluate(hasText("API1:2023")),
    "no OWASP category badge found",
  );
  check(
    "findings render with risk scores",
    await evaluate(hasText("Critical")),
    "no risk score rendered",
  );
  check(
    "severity filter chips are present",
    (await evaluate("document.querySelectorAll('.chip').length")) >= 5,
    "fewer than five severity chips",
  );
  await shot("scan-results");

  // Filter to critical only and confirm the list narrows.
  const beforeFilter = await evaluate(
    "document.querySelectorAll('.finding-card').length",
  );
  await clickSelector(
    "[...document.querySelectorAll('.chip')].find((c) => c.textContent.includes('Critical'))",
    "critical severity chip",
  );
  await delay(300);
  const afterFilter = await evaluate(
    "document.querySelectorAll('.finding-card').length",
  );
  check(
    "severity filter narrows the finding list",
    afterFilter > 0 && afterFilter <= beforeFilter,
    `before=${beforeFilter} after=${afterFilter}`,
  );
  await shot("scan-results-filtered");

  // Reset the filter, then open a finding detail dialog.
  await clickSelector(
    "[...document.querySelectorAll('.chip.is-active')][0] ?? [...document.querySelectorAll('button')].find((b) => b.textContent.includes('Clear filters'))",
    "active filter chip",
  );
  await delay(300);
  await clickSelector(
    "document.querySelector('.finding-card button')",
    "finding details",
  );
  await waitFor("document.querySelector('[role=dialog]') !== null", "detail dialog");
  const dialogText = await evaluate(
    "document.querySelector('[role=dialog]').innerText",
  );
  check(
    "finding detail dialog shows category and confidence",
    dialogText.includes("OWASP category") && dialogText.includes("Confidence"),
  );
  check(
    "evidence block is captured",
    dialogText.includes("Evidence"),
    "no evidence section in the dialog",
  );
  await shot("finding-detail");

  await clickSelector(
    "[...document.querySelectorAll('[role=dialog] button')].find((b) => b.textContent.trim() === 'Close')",
    "close dialog",
  );
  await waitFor("document.querySelector('[role=dialog]') === null", "dialog close");

  // Dark theme.
  await clickSelector(
    "document.querySelector('button[aria-label=\"Dark theme\"]')",
    "dark theme toggle",
  );
  await delay(300);
  check(
    "dark theme applies to the document",
    (await evaluate("document.documentElement.dataset.theme")) === "dark",
  );
  await shot("scan-results-dark");

  // Back to the light theme.
  await clickSelector(
    "document.querySelector('button[aria-label=\"Light theme\"]')",
    "light theme toggle",
  );
  await delay(250);

  /* --------------------------- mutations ------------------------------ */

  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => a.getAttribute('href') === '/projects')",
    "projects nav link",
  );
  await waitFor(hasText("All projects"), "projects page");

  await clickSelector(
    "[...document.querySelectorAll('button')].find((b) => b.textContent.includes('New project'))",
    "new project button",
  );
  await waitFor("document.querySelector('#project-form input') !== null", "project dialog");
  await evaluate(`(() => {
    const input = document.querySelector('#project-form input');
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(input, 'Smoke test project');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);
  await clickSelector(
    "document.querySelector('button[form=project-form]')",
    "create project",
  );
  await waitFor(
    "/^\\/projects\\/\\d+$/.test(location.pathname) && document.body.innerText.includes('Smoke test project')",
    "new project page",
  );
  check("creating a project opens it", true);
  await shot("project-created");

  // Run a scan through the authorization acknowledgement gate.
  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => a.getAttribute('href') === '/projects')",
    "projects nav link",
  );
  await waitFor(hasText("All projects"), "projects list");
  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => a.getAttribute('href') === '/projects/1')",
    "first project link",
  );
  await waitFor(hasText("Payments API (staging)"), "project targets");
  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => a.getAttribute('href') === '/targets/1')",
    "target link",
  );
  await waitFor(hasText("/api/v1/orders"), "target endpoints");
  await clickSelector(
    "[...document.querySelectorAll('button')].find((b) => b.textContent.includes('Run scan'))",
    "run scan button",
  );
  await waitFor("document.querySelector('.modal .checkbox input') !== null", "scan dialog");
  const acknowledgedBefore = await evaluate(
    "document.querySelector('.modal button.btn--primary').disabled",
  );
  check(
    "scan dialog requires the authorization acknowledgement",
    acknowledgedBefore === true,
    "start button was enabled before acknowledging",
  );
  await clickSelector("document.querySelector('.modal .checkbox input')", "acknowledgement");
  await clickSelector(
    "[...document.querySelectorAll('.modal button')].find((b) => b.textContent.includes('Start scan'))",
    "start scan",
  );
  await waitFor(
    "location.pathname.startsWith('/targets/1/scans/')",
    "scan results navigation",
    30000,
  );
  await waitFor(
    "document.querySelectorAll('.finding-card').length > 0",
    "findings from the new scan",
    30000,
  );
  check("a new scan runs and results load", true);
  await shot("scan-completed");

  /* ------------------------ desktop layout sanity ---------------------- */

  await clickSelector(
    "[...document.querySelectorAll('a')].find((a) => a.getAttribute('href') === '/')",
    "dashboard nav link",
  );
  await waitFor(
    "document.querySelector('.recharts-surface') !== null",
    "dashboard charts",
  );
  check(
    "in-app navigation keeps the session",
    await evaluate(hasText("Dashboard")),
  );

  // The design system must actually be applied: geometry, tokens and
  // overflow are asserted here because the smoke test cannot inspect pixels.
  const layout = await evaluate(`(() => {
    const sidebar = document.querySelector('.sidebar');
    const sidebarBox = sidebar.getBoundingClientRect();
    const primary = document.querySelector('.btn--primary');
    const cell = document.querySelector('.table td');
    const bodyStyle = getComputedStyle(document.body);
    const overflowing = [...document.querySelectorAll('.card, .table-wrap, .finding-card')]
      .filter((el) => el.scrollWidth - el.clientWidth > 2).length;
    return {
      viewport: window.innerWidth,
      pageOverflow: document.documentElement.scrollWidth - window.innerWidth,
      sidebarWidth: Math.round(sidebarBox.width),
      sidebarAtLeft: sidebarBox.left === 0,
      sidebarIsSticky: getComputedStyle(sidebar).position === 'sticky',
      bodyBackground: bodyStyle.backgroundColor,
      fontFamily: bodyStyle.fontFamily,
      primaryBackground: primary ? getComputedStyle(primary).backgroundColor : null,
      primaryRadius: primary ? getComputedStyle(primary).borderRadius : null,
      cellBorder: cell ? getComputedStyle(cell).borderBottomWidth : null,
      chartSurfaces: document.querySelectorAll('.recharts-surface').length,
      overflowing,
      topbarSticky: getComputedStyle(document.querySelector('.topbar')).position === 'sticky',
    };
  })()`);

  check(
    "shell renders as a two-column layout",
    layout.sidebarWidth === 264 && layout.sidebarAtLeft && layout.sidebarIsSticky,
    `sidebar=${layout.sidebarWidth}px left=${layout.sidebarAtLeft} sticky=${layout.sidebarIsSticky}`,
  );
  check(
    "top bar stays sticky",
    layout.topbarSticky,
    "topbar is not sticky",
  );
  check(
    "no horizontal overflow at desktop width",
    layout.pageOverflow <= 1 && layout.overflowing === 0,
    `pageOverflow=${layout.pageOverflow}px overflowingContainers=${layout.overflowing}`,
  );
  check(
    "design tokens apply (surface, font, accent)",
    layout.bodyBackground === "rgb(244, 246, 251)" &&
      layout.fontFamily.includes("Segoe UI") &&
      layout.primaryBackground === "rgb(79, 70, 229)" &&
      layout.primaryRadius !== "0px",
    `bg=${layout.bodyBackground} font=${layout.fontFamily} primary=${layout.primaryBackground} radius=${layout.primaryRadius}`,
  );
  check(
    "table styling is applied",
    layout.cellBorder !== null && layout.cellBorder !== "0px",
    `cellBorder=${layout.cellBorder}`,
  );
  check(
    "charts render as SVG",
    layout.chartSurfaces >= 1,
    `chartSurfaces=${layout.chartSurfaces}`,
  );

  /* -------------------------- mobile layout --------------------------- */

  await devtools.send(
    "Emulation.setDeviceMetricsOverride",
    { width: 390, height: 844, deviceScaleFactor: 2, mobile: true },
    session,
  );
  await delay(400);
  const mobile = await evaluate(`(() => {
    const sidebar = document.querySelector('.sidebar');
    const toggle = document.querySelector('.nav-toggle');
    return {
      sidebarTransform: getComputedStyle(sidebar).transform,
      sidebarLeft: Math.round(sidebar.getBoundingClientRect().left),
      toggleVisible: toggle !== null && getComputedStyle(toggle).display !== 'none',
      pageOverflow: document.documentElement.scrollWidth - window.innerWidth,
    };
  })()`);
  check(
    "narrow viewports collapse the sidebar off-canvas",
    mobile.sidebarLeft < 0 && mobile.toggleVisible,
    `sidebarLeft=${mobile.sidebarLeft}px toggle=${mobile.toggleVisible}`,
  );
  check(
    "no horizontal overflow on mobile",
    mobile.pageOverflow <= 1,
    `pageOverflow=${mobile.pageOverflow}px`,
  );
  await shot("dashboard-mobile");

  await clickSelector("document.querySelector('.nav-toggle')", "nav toggle");
  await delay(400);
  const drawerLeft = await evaluate(
    "Math.round(document.querySelector('.sidebar').getBoundingClientRect().left)",
  );
  check(
    "the nav drawer opens on mobile",
    drawerLeft >= -1,
    `sidebarLeft=${drawerLeft}px`,
  );
  await shot("dashboard-mobile-nav");
  await devtools.send("Emulation.clearDeviceMetricsOverride", {}, session);

  check(
    "no console errors or uncaught exceptions",
    consoleErrors.length === 0,
    consoleErrors.join(" | ").slice(0, 500),
  );

  chrome.kill();

  const failed = results.filter((result) => !result.ok);
  console.log(
    `\n${results.length - failed.length}/${results.length} checks passed · ${screenshots} screenshots in ${OUT_DIR}\n`,
  );
  if (failed.length > 0) {
    process.exitCode = 1;
  }
  // Exit explicitly: a detached Chrome child can keep the event loop alive.
  setTimeout(() => process.exit(process.exitCode ?? 0), 750).unref();
}

main().catch((error) => {
  console.error(`\nUI smoke test failed: ${error.message}\n`);
  chromeProcess?.kill();
  setTimeout(() => process.exit(1), 750).unref();
});
