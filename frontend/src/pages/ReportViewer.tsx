import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  downloadReport,
  getReport,
  listScans,
  startScan,
  type ReportData,
  type Scan,
} from "../api/client";

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

const CATEGORY_LABELS: Record<string, string> = {
  "api1:2023": "API1: Broken Object Level Authorization",
  "api2:2023": "API2: Broken Authentication",
  "api3:2023": "API3: Broken Object Property Level Authorization",
  "api4:2023": "API4: Unrestricted Resource Consumption",
  "api5:2023": "API5: Broken Function Level Authorization",
  "api6:2023": "API6: Unrestricted Access to Sensitive Business Flows",
  "api7:2023": "API7: Server-Side Request Forgery",
  "api8:2023": "API8: Security Misconfiguration",
  "api9:2023": "API9: Improper Inventory Management",
  "api10:2023": "API10: Unsafe Consumption of APIs",
};

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 120_000;

function severityLabel(severity: string): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

export default function ReportViewer() {
  const { targetId } = useParams();
  const target = Number(targetId);
  const [scans, setScans] = useState<Scan[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<number | null>(null);
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (Number.isNaN(target)) {
      setError("Invalid target id");
      setLoading(false);
      return;
    }
    let cancelled = false;
    async function loadLatest() {
      try {
        const all = await listScans(target);
        if (cancelled) {
          return;
        }
        setScans(all);
        const latest = all[0];
        if (latest !== undefined) {
          setSelectedScanId(latest.id);
          setReport(await getReport(latest.id));
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load scan results",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void loadLatest();
    return () => {
      cancelled = true;
    };
  }, [target]);

  async function selectScan(scanId: number) {
    setError(null);
    setSelectedScanId(scanId);
    try {
      setReport(await getReport(scanId));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load scan results",
      );
    }
  }

  async function handleRunScan() {
    setError(null);
    setRunning(true);
    try {
      await startScan(target);
      const deadline = Date.now() + POLL_TIMEOUT_MS;
      while (Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
        const all = await listScans(target);
        setScans(all);
        const latest = all[0];
        const finished = latest !== undefined &&
          (latest.status === "completed" ||
            latest.status === "completed_with_errors" ||
            latest.status === "failed");
        if (finished && latest.id !== selectedScanId) {
          setSelectedScanId(latest.id);
          setReport(await getReport(latest.id));
          return;
        }
      }
      setError("Scan is taking longer than expected — refresh to check.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start scan");
    } finally {
      setRunning(false);
    }
  }

  const findings = report
    ? [...report.findings].sort((a, b) => {
        const severityDiff =
          (SEVERITY_ORDER[a.severity] ?? 99) -
          (SEVERITY_ORDER[b.severity] ?? 99);
        return severityDiff !== 0
          ? severityDiff
          : b.risk_score - a.risk_score;
      })
    : [];

  return (
    <section>
      <p>
        <Link to="/projects">← Back to projects</Link>
      </p>
      <h2>Scan Results</h2>

      {error !== null && <p role="alert">{error}</p>}

      <button
        type="button"
        onClick={handleRunScan}
        disabled={running || Number.isNaN(target)}
      >
        {running ? "Scan running…" : "Run new scan"}
      </button>

      {scans.length > 0 && (
        <p>
          <label>
            Scan{" "}
            <select
              value={selectedScanId ?? undefined}
              onChange={(event) => selectScan(Number(event.target.value))}
            >
              {scans.map((scan) => (
                <option key={scan.id} value={scan.id}>
                  #{scan.id} ({scan.status})
                </option>
              ))}
            </select>
          </label>
        </p>
      )}

      {loading && <p>Loading…</p>}

      {!loading && report === null && !error && (
        <p>No scans yet — run a scan to see results.</p>
      )}

      {report !== null && (
        <>
          <h3>Latest scan #{report.metadata.scan_id}</h3>
          <p>
            {report.metadata.target_name} ({report.metadata.base_url}) —{" "}
            status: {report.metadata.status}
          </p>

          <h4>Summary</h4>
          <ul>
            <li>Critical: {report.summary.critical}</li>
            <li>High: {report.summary.high}</li>
            <li>Medium: {report.summary.medium}</li>
            <li>Low: {report.summary.low}</li>
            <li>Info: {report.summary.info}</li>
            <li>
              <strong>Total: {report.summary.total}</strong>
            </li>
          </ul>

          <h4>Download report</h4>
          <p>
            <button
              type="button"
              onClick={() => void downloadReport(report.metadata.scan_id, "html")}
            >
              HTML
            </button>{" "}
            <button
              type="button"
              onClick={() => void downloadReport(report.metadata.scan_id, "pdf")}
            >
              PDF
            </button>{" "}
            <button
              type="button"
              onClick={() => void downloadReport(report.metadata.scan_id, "json")}
            >
              JSON
            </button>
          </p>

          <h4>Findings ({findings.length})</h4>
          {findings.length === 0 ? (
            <p>No findings for this scan.</p>
          ) : (
            findings.map((finding) => (
              <article
                key={finding.id}
                style={{
                  border: "1px solid #ccc",
                  borderLeft: `4px solid ${severityColor(finding.severity)}`,
                  borderRadius: 4,
                  margin: "0.75rem 0",
                  padding: "0.5rem 0.75rem",
                }}
              >
                <p>
                  <strong>{finding.title}</strong>{" "}
                  <span className={`badge severity-${finding.severity}`}>
                    {severityLabel(finding.severity)}
                  </span>{" "}
                  <span className="badge risk">
                    Risk: {finding.risk_label} ({finding.risk_score}/10)
                  </span>
                </p>
                <p>{finding.description}</p>
                <p>
                  <code>{finding.endpoint}</code>
                </p>
                <p>
                  <span className="badge category">
                    {CATEGORY_LABELS[finding.owasp_category] ??
                      finding.owasp_category}
                  </span>{" "}
                  Confidence: {finding.confidence}
                </p>
                {finding.evidence !== null && (
                  <details>
                    <summary>Evidence ({finding.evidence.scanner_name})</summary>
                    <pre>{finding.evidence.request_data}</pre>
                    <pre>{finding.evidence.response_data}</pre>
                  </details>
                )}
              </article>
            ))
          )}
        </>
      )}

      <style>{`
        .badge {
          display: inline-block;
          border-radius: 9999px;
          padding: 0.1rem 0.6rem;
          font-size: 0.75rem;
          font-weight: 600;
          color: #fff;
        }
        .badge.severity-critical { background: #b91c1c; }
        .badge.severity-high { background: #ea580c; }
        .badge.severity-medium { background: #d97706; }
        .badge.severity-low { background: #16a34a; }
        .badge.severity-info { background: #64748b; }
        .badge.risk { background: #2563eb; }
        .badge.category { background: #7c3aed; }
        details pre {
          background: #f4f4f5;
          border-radius: 4px;
          padding: 0.5rem;
          white-space: pre-wrap;
          word-break: break-word;
        }
      `}</style>
    </section>
  );
}

function severityColor(severity: string): string {
  switch (severity) {
    case "critical":
      return "#b91c1c";
    case "high":
      return "#ea580c";
    case "medium":
      return "#d97706";
    case "low":
      return "#16a34a";
    default:
      return "#64748b";
  }
}
