import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  downloadReport,
  getReport,
  getTarget,
  listScans,
  startScan,
  type ReportData,
  type ReportFinding,
} from "../api/client";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import Badge, { SeverityBadge, StatusBadge } from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import CopyButton from "../components/ui/CopyButton";
import {
  EmptyState,
  ErrorAlert,
  InfoAlert,
  SkeletonList,
} from "../components/ui/Feedback";
import { SelectInput, TextInput } from "../components/ui/Field";
import Modal from "../components/ui/Modal";
import { useToast } from "../components/ui/Toaster";
import { useAsyncData } from "../hooks/useAsyncData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  SEVERITIES,
  categoryBreakdown,
  confidenceLabel,
  filterFindings,
  formatEvidenceBody,
  isScanActive,
  isScanFinished,
  owaspLabel,
  severityLabel,
  sortFindings,
  summarizeFindings,
  toggleSeverity,
} from "../lib/domain";
import { cx } from "../lib/cx";
import {
  formatDateTime,
  formatDuration,
  formatNumber,
  pluralize,
} from "../lib/format";

const POLL_INTERVAL_MS = 2500;
const POLL_TIMEOUT_MS = 180_000;

type SortKey = "severity" | "risk" | "endpoint" | "title";

export default function ScanResults() {
  const { targetId, scanId } = useParams();
  const id = Number(targetId);
  const scan = Number(scanId);
  const navigate = useNavigate();
  const toast = useToast();

  const target = useAsyncData(() => getTarget(id), [id], {
    enabled: Number.isFinite(id),
  });
  const scans = useAsyncData(() => listScans(id), [id], {
    enabled: Number.isFinite(id),
  });
  const report = useAsyncData(() => getReport(scan), [scan], {
    enabled: Number.isFinite(scan),
  });

  const [query, setQuery] = useState("");
  const [severities, setSeverities] = useState<string[]>([]);
  const [category, setCategory] = useState("all");
  const [sort, setSort] = useState<SortKey>("severity");
  const [detail, setDetail] = useState<ReportFinding | null>(null);
  const [running, setRunning] = useState(false);
  const [scanOpen, setScanOpen] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  const data: ReportData | null = report.data;
  const status = data?.metadata.status ?? null;

  useDocumentTitle(data !== null ? `Scan #${data.metadata.scan_id}` : "Scan");

  // While a scan is queued or running, poll the report until it settles.
  useEffect(() => {
    if (status === null || isScanFinished(status) || !Number.isFinite(scan)) {
      return;
    }
    const timer = window.setInterval(() => {
      report.reload();
      scans.reload();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
    // Re-arm only when the scan or its status changes.
  }, [status, scan]);

  const findings = data?.findings ?? [];
  const summary = summarizeFindings(findings);
  const categories = categoryBreakdown(findings);
  const visible = sortFindings(
    filterFindings(findings, {
      query,
      severities,
      category: category === "all" ? null : category,
    }),
    sort,
  );

  const filtersActive =
    query.trim() !== "" || severities.length > 0 || category !== "all";

  async function handleExport(format: "html" | "pdf" | "json") {
    if (data === null) {
      return;
    }
    setDownloading(format);
    try {
      await downloadReport(data.metadata.scan_id, format);
      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch (err) {
      toast.error(
        "Export failed",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setDownloading(null);
    }
  }

  async function handleRunScan() {
    setScanOpen(false);
    setRunning(true);
    try {
      const queued = await startScan(id);
      toast.info("Scan queued", "Results will open when it finishes.");
      const deadline = Date.now() + POLL_TIMEOUT_MS;
      while (Date.now() < deadline) {
        await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
        const latest = await listScans(id);
        scans.setData(latest);
        // Watch the scan we queued rather than whichever scan is newest: an
        // older completed scan must not be mistaken for this run.
        const watched = latest.find((scan) => scan.id === queued.scan_id);
        if (watched !== undefined && isScanFinished(watched.status)) {
          if (watched.status === "failed") {
            toast.error(
              "Scan failed",
              "The worker could not complete this scan. Check the worker logs.",
            );
          } else {
            toast.success(
              "Scan finished",
              `Scan #${watched.id} is ${watched.status.replace(/_/g, " ")}.`,
            );
          }
          navigate(`/targets/${id}/scans/${watched.id}`);
          return;
        }
      }
      toast.error(
        "Scan is still running",
        "It is taking longer than expected — reopen this page to check.",
      );
    } catch (err) {
      toast.error(
        "Scan could not be started",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setRunning(false);
    }
  }

  function clearFilters() {
    setQuery("");
    setSeverities([]);
    setCategory("all");
  }

  if (!Number.isFinite(id) || !Number.isFinite(scan)) {
    return (
      <div className="page">
        <ErrorAlert title="Invalid URL">
          This page needs both a target id and a scan id.
        </ErrorAlert>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title={data !== null ? `Scan #${data.metadata.scan_id}` : "Scan results"}
        subtitle={
          data !== null ? (
            <span className="row row--wrap">
              <span>{data.metadata.project_name}</span>
              <span className="subtle">/</span>
              <span>{data.metadata.target_name}</span>
              <span className="mono subtle break-all">
                {data.metadata.base_url}
              </span>
            </span>
          ) : undefined
        }
        breadcrumbs={[
          { label: "Projects", to: "/projects" },
          {
            label: data?.metadata.project_name ?? "Project",
            to: data !== null ? `/projects/${data.metadata.project_id}` : undefined,
          },
          { label: target.data?.name ?? "Target", to: `/targets/${id}` },
          { label: `Scan #${scan}` },
        ]}
        actions={
          <>
            <Button
              icon={<Icon name="download" size={16} />}
              loading={downloading === "html"}
              disabled={data === null}
              onClick={() => void handleExport("html")}
            >
              HTML
            </Button>
            <Button
              icon={<Icon name="download" size={16} />}
              loading={downloading === "pdf"}
              disabled={data === null}
              onClick={() => void handleExport("pdf")}
            >
              PDF
            </Button>
            <Button
              icon={<Icon name="download" size={16} />}
              loading={downloading === "json"}
              disabled={data === null}
              onClick={() => void handleExport("json")}
            >
              JSON
            </Button>
            <Button
              variant="primary"
              loading={running}
              onClick={() => {
                setAcknowledged(false);
                setScanOpen(true);
              }}
              icon={<Icon name="play" size={16} />}
            >
              {running ? "Scanning…" : "Run new scan"}
            </Button>
          </>
        }
      />

      {report.error !== null && (
        <ErrorAlert
          title="Could not load this scan"
          action={
            <>
              <Button onClick={() => report.reload()}>Try again</Button>
              <Link className="btn btn--ghost" to={`/targets/${id}`}>
                Back to target
              </Link>
            </>
          }
        >
          {report.error}
        </ErrorAlert>
      )}

      {report.loading && data === null && <SkeletonList rows={3} />}

      {(scans.data?.length ?? 0) > 0 && (
        <Card bodyClassName="card__body--tight">
          <div className="toolbar">
            <label className="row small strong" htmlFor="scan-select">
              Scan
            </label>
            <SelectInput
              id="scan-select"
              value={scan}
              onChange={(event) =>
                navigate(`/targets/${id}/scans/${event.target.value}`)
              }
              style={{ maxWidth: "16rem" }}
            >
              {(scans.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  #{item.id} · {item.status.replace(/_/g, " ")} ·{" "}
                  {formatDateTime(item.started_at)}
                </option>
              ))}
            </SelectInput>
            <div className="toolbar__spacer" />
            {status !== null && (
              <span className="row">
                <StatusBadge status={status} />
                {data?.metadata.started_at != null && (
                  <span className="small subtle">
                    started {formatDateTime(data.metadata.started_at)}
                  </span>
                )}
                {data !== null && (
                  <span className="small subtle">
                    ·{" "}
                    {formatDuration(
                      data.metadata.started_at,
                      data.metadata.finished_at,
                    ) ?? "in progress"}
                  </span>
                )}
              </span>
            )}
          </div>
        </Card>
      )}

      {data !== null && isScanActive(data.metadata.status) && (
        <InfoAlert tone="info" title="Scan in progress">
          Scanners are still working through this target. Findings appear here
          automatically as soon as the run finishes.
        </InfoAlert>
      )}

      {data !== null && (
        <>
          <Card
            title="Summary"
            subtitle={pluralize(summary.total, "finding")}
            actions={
              filtersActive ? (
                <Button size="sm" variant="ghost" onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : undefined
            }
          >
            <div className="severity-bar" role="presentation">
              {SEVERITIES.filter(
                (severity) =>
                  findings.filter((finding) => finding.severity === severity)
                    .length > 0,
              ).map((severity) => {
                const count = findings.filter(
                  (finding) => finding.severity === severity,
                ).length;
                return (
                  <span
                    key={severity}
                    className={`severity-bar__seg severity-bar__seg--${severity}`}
                    style={{ flexGrow: count }}
                    title={`${severityLabel(severity)}: ${count}`}
                  />
                );
              })}
            </div>
            <div className="chip-row">
              {SEVERITIES.map((severity) => {
                const count = findCount(findings, severity);
                return (
                  <button
                    key={severity}
                    type="button"
                    className={cx(
                      "chip",
                      severities.includes(severity) && "is-active",
                    )}
                    aria-pressed={severities.includes(severity)}
                    onClick={() =>
                      setSeverities((current) =>
                        toggleSeverity(current, severity),
                      )
                    }
                    disabled={count === 0}
                  >
                    <span
                      className={`chip__swatch swatch--${severity}`}
                      aria-hidden="true"
                    />
                    {severityLabel(severity)}
                    <span className="chip__count">{count}</span>
                  </button>
                );
              })}
              <Badge tone="accent">Total {formatNumber(summary.total)}</Badge>
            </div>
          </Card>

          <Card
            title="Findings"
            subtitle={`${formatNumber(visible.length)} shown of ${formatNumber(
              findings.length,
            )}`}
          >
            {findings.length === 0 ? (
              <EmptyState
                icon="shield-check"
                title="No findings for this scan"
                text="Every scanner ran without flagging an issue on the imported endpoints. Re-run after changing the target's configuration."
              />
            ) : (
              <>
                <div className="toolbar">
                  <div className="search grow">
                    <span className="search__icon">
                      <Icon name="search" size={15} />
                    </span>
                    <TextInput
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Search title, endpoint, category…"
                      aria-label="Search findings"
                    />
                  </div>
                  <div className="toolbar__group">
                    <label className="small subtle" htmlFor="category-filter">
                      Category
                    </label>
                    <SelectInput
                      id="category-filter"
                      value={category}
                      onChange={(event) => setCategory(event.target.value)}
                      style={{ minWidth: "13rem" }}
                    >
                      <option value="all">All categories</option>
                      {categories.map((item) => (
                        <option key={item.code} value={item.code}>
                          {item.short} · {item.label} ({item.count})
                        </option>
                      ))}
                    </SelectInput>
                  </div>
                  <div className="toolbar__group">
                    <label className="small subtle" htmlFor="sort-select">
                      Sort
                    </label>
                    <SelectInput
                      id="sort-select"
                      value={sort}
                      onChange={(event) => setSort(event.target.value as SortKey)}
                      style={{ minWidth: "10rem" }}
                    >
                      <option value="severity">Severity</option>
                      <option value="risk">Risk score</option>
                      <option value="endpoint">Endpoint</option>
                      <option value="title">Title</option>
                    </SelectInput>
                  </div>
                </div>

                {visible.length === 0 ? (
                  <EmptyState
                    icon="filter"
                    title="No findings match the filters"
                    text="Loosen the severity, category or search filters to see more."
                    action={<Button onClick={clearFilters}>Clear filters</Button>}
                  />
                ) : (
                  <div className="stack">
                    {visible.map((finding) => (
                      <article
                        className={`finding-card finding-card--${finding.severity}`}
                        key={finding.id}
                      >
                        <div className="row row--wrap">
                          <SeverityBadge severity={finding.severity} />
                          <span className="finding-card__title grow">
                            {finding.title}
                          </span>
                          <span className="risk-meter">
                            <span className="risk-meter__track">
                              <span
                                className={`risk-meter__fill risk-meter__fill--${finding.risk_label.toLowerCase()}`}
                                style={{
                                  width: `${Math.min(100, finding.risk_score * 10)}%`,
                                }}
                              />
                            </span>
                            {finding.risk_label} ·{" "}
                            {finding.risk_score.toFixed(1)}/10
                          </span>
                        </div>
                        <p className="finding-card__desc">{finding.description}</p>
                        <div className="row row--wrap">
                          <span className="endpoint-line">
                            <Icon name="target" size={14} />
                            {finding.endpoint}
                          </span>
                          <Badge tone="accent" title={owaspLabel(finding.owasp_category)}>
                            {owaspLabel(finding.owasp_category)}
                          </Badge>
                          <Badge outline>{confidenceLabel(finding.confidence)}</Badge>
                          <div className="toolbar__spacer" />
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setDetail(finding)}
                          >
                            Details
                          </Button>
                        </div>
                        {finding.evidence !== null && (
                          <details>
                            <summary className="small strong">
                              Evidence ({finding.evidence.scanner_name})
                            </summary>
                            <div className="stack stack--sm" style={{ marginTop: "0.75rem" }}>
                              {finding.evidence_text != null && (
                                <EvidenceBlock
                                  label="Captured"
                                  body={finding.evidence_text}
                                />
                              )}
                              <EvidenceBlock
                                label="Request"
                                body={finding.evidence.request_data}
                              />
                              <EvidenceBlock
                                label="Response"
                                body={finding.evidence.response_data}
                              />
                            </div>
                          </details>
                        )}
                      </article>
                    ))}
                  </div>
                )}
              </>
            )}
          </Card>
        </>
      )}

      <Modal
        open={scanOpen}
        onClose={() => setScanOpen(false)}
        title="Run a new scan"
        subtitle="Scanners send live requests to the target from the worker container."
        footer={
          <>
            <Button
              variant="primary"
              disabled={!acknowledged}
              onClick={() => void handleRunScan()}
              icon={<Icon name="play" size={16} />}
            >
              Start scan
            </Button>
            <Button variant="ghost" onClick={() => setScanOpen(false)}>
              Cancel
            </Button>
          </>
        }
      >
        <InfoAlert tone="warning" title="Authorization required">
          Only scan targets you are authorised to test. A scan sends live
          requests to {data?.metadata.base_url ?? "the target"}.
        </InfoAlert>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
          />
          <span className="checkbox__text">
            I confirm I have written authorization to send test requests to this
            target, and that the scope matches the engagement.
          </span>
        </label>
      </Modal>

      <Modal
        open={detail !== null}
        onClose={() => setDetail(null)}
        wide
        title={detail?.title ?? "Finding"}
        subtitle={
          detail !== null
            ? `${severityLabel(detail.severity)} · ${owaspLabel(detail.owasp_category)}`
            : undefined
        }
        footer={
          <>
            {detail !== null && (
              <Badge tone="accent">
                Risk {detail.risk_label} ({detail.risk_score.toFixed(1)}/10)
              </Badge>
            )}
            <div className="toolbar__spacer" />
            <Button variant="secondary" onClick={() => setDetail(null)}>
              Close
            </Button>
          </>
        }
      >
        {detail !== null && (
          <>
            <p>{detail.description}</p>
            <dl className="def-list">
              <dt>Endpoint</dt>
              <dd className="row">
                <span className="mono break-all">{detail.endpoint}</span>
                <CopyButton value={detail.endpoint} />
              </dd>
              {detail.evidence_text != null && (
                <>
                  <dt>Scanner evidence</dt>
                  <dd className="mono break-all">{detail.evidence_text}</dd>
                </>
              )}
              <dt>OWASP category</dt>
              <dd>{owaspLabel(detail.owasp_category)}</dd>
              <dt>Confidence</dt>
              <dd>{confidenceLabel(detail.confidence)}</dd>
              <dt>Risk score</dt>
              <dd>
                {detail.risk_label} ({detail.risk_score.toFixed(1)}/10)
              </dd>
              <dt>Detected</dt>
              <dd>{formatDateTime(detail.created_at)}</dd>
              <dt>Finding id</dt>
              <dd>#{detail.id}</dd>
            </dl>
            {detail.evidence !== null && (
              <div className="stack stack--sm">
                <span className="field__label">
                  Evidence · {detail.evidence.scanner_name}
                </span>
                <EvidenceBlock
                  label="Request"
                  body={detail.evidence.request_data}
                />
                <EvidenceBlock
                  label="Response"
                  body={detail.evidence.response_data}
                />
              </div>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}

function findCount(findings: ReportFinding[], severity: string): number {
  return findings.filter((finding) => finding.severity === severity).length;
}

function EvidenceBlock({ label, body }: { label: string; body: string | null }) {
  const text = formatEvidenceBody(body);
  return (
    <div>
      <div className="code-block__header">
        <span>{label}</span>
        <div className="toolbar__spacer" />
        {text !== "" && <CopyButton value={text} />}
      </div>
      <pre className="code-block">{text === "" ? "Not captured" : text}</pre>
    </div>
  );
}
