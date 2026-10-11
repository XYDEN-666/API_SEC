import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getDashboardSummary } from "../api/client";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import Badge, { SeverityBadge, StatusBadge } from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Card, { StatCard } from "../components/ui/Card";
import { EmptyState, ErrorAlert, SkeletonList } from "../components/ui/Feedback";
import { useAsyncData } from "../hooks/useAsyncData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  SEVERITIES,
  categoryBreakdownFromCounts,
  severityColor,
  severityLabel,
} from "../lib/domain";
import { formatNumber, formatRelative, pluralize } from "../lib/format";

const SERIES_COLORS = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
  "var(--series-9)",
  "var(--series-10)",
];

const TOOLTIP_STYLE = {
  background: "var(--chart-surface)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  boxShadow: "var(--shadow-md)",
  color: "var(--chart-ink)",
  fontSize: "0.8125rem",
};

export default function Dashboard() {
  const summary = useAsyncData(() => getDashboardSummary(), []);
  useDocumentTitle("Dashboard");

  const data = summary.data;
  const isEmpty =
    data !== null &&
    data.total_projects === 0 &&
    data.total_scans === 0 &&
    data.total_findings === 0;

  // Severity rows are built from the aggregate table on the dashboard, so the
  // legend stays stable even when a severity has no findings.
  const severityRows = SEVERITIES.map((severity) => ({
    severity,
    label: severityLabel(severity),
    color: severityColor(severity),
    count: data?.findings_by_severity[severity] ?? 0,
  }));
  const severityData = severityRows.filter((row) => row.count > 0);
  const categoryRows =
    data === null ? [] : categoryBreakdownFromCounts(data.findings_by_category);
  const labelByShort = new Map(
    categoryRows.map((row) => [row.short, row.label]),
  );

  return (
    <div className="page">
      <PageHeader
        title="Dashboard"
        subtitle="Aggregate posture across every project you own."
        actions={
          <>
            <Button
              onClick={summary.reload}
              loading={summary.loading}
              icon={<Icon name="refresh" size={16} />}
            >
              Refresh
            </Button>
            <Link className="btn btn--primary" to="/projects">
              <Icon name="plus" size={16} />
              New project
            </Link>
          </>
        }
      />

      {summary.error !== null && (
        <ErrorAlert action={<Button onClick={summary.reload}>Try again</Button>}>
          {summary.error}
        </ErrorAlert>
      )}

      {summary.loading && summary.data === null && <SkeletonList rows={3} />}

      {data !== null && (
        <>
          <div className="grid grid--4">
            <StatCard
              label="Projects"
              value={formatNumber(data.total_projects)}
              icon={<Icon name="folder" size={20} />}
            />
            <StatCard
              label="Targets"
              value={formatNumber(data.total_targets)}
              icon={<Icon name="target" size={20} />}
              tone="info"
            />
            <StatCard
              label="Scans run"
              value={formatNumber(data.total_scans)}
              icon={<Icon name="activity" size={20} />}
              tone="success"
            />
            <StatCard
              label="Findings"
              value={formatNumber(data.total_findings)}
              icon={<Icon name="shield" size={20} />}
              tone={data.total_findings > 0 ? "danger" : "success"}
              hint={
                data.total_findings > 0
                  ? pluralize(data.total_distinct_issues, "distinct issue")
                  : undefined
              }
            />
          </div>

          {isEmpty && (
            <Card
              title="Get your first scan running"
              subtitle="Three steps from an empty workspace to a triaged report."
            >
              <ol className="grid grid--3">
                {[
                  {
                    title: "Create a project",
                    text: "A project groups the targets belonging to one engagement.",
                  },
                  {
                    title: "Add a target and import its spec",
                    text: "Add the base URL, then upload the OpenAPI 3.x document.",
                  },
                  {
                    title: "Run a scan and triage",
                    text: "Findings arrive with severity, OWASP category and evidence.",
                  },
                ].map((step, index) => (
                  <li className="card" key={step.title}>
                    <div className="card__body card__body--tight">
                      <span className="badge badge--accent">
                        Step {index + 1}
                      </span>
                      <span className="strong">{step.title}</span>
                      <span className="small muted">{step.text}</span>
                    </div>
                  </li>
                ))}
              </ol>
              <div className="row">
                <Link className="btn btn--primary" to="/projects">
                  <Icon name="plus" size={16} />
                  Create a project
                </Link>
              </div>
            </Card>
          )}

          <div className="grid grid--2">
            <Card
              title="Findings by severity"
              subtitle={pluralize(data.total_findings, "finding")}
            >
              {severityData.length === 0 ? (
                <EmptyState
                  icon="shield-check"
                  title="No findings yet"
                  text="Run a scan on a target and the severity split appears here."
                />
              ) : (
                <div className="row" style={{ alignItems: "center", gap: "2rem" }}>
                  <div style={{ width: 200, height: 200, flex: "none" }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={severityData}
                          dataKey="count"
                          nameKey="label"
                          innerRadius={54}
                          outerRadius={86}
                          paddingAngle={2}
                          stroke="none"
                        >
                          {severityData.map((row) => (
                            <Cell key={row.severity} fill={row.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={TOOLTIP_STYLE}
                          itemStyle={{ color: "var(--chart-ink)" }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="legend grow">
                    {severityRows.map((row) => (
                      <div className="legend__item" key={row.severity}>
                        <span
                          className={`chip__swatch swatch--${row.severity}`}
                          aria-hidden="true"
                        />
                        <span className="legend__label">{row.label}</span>
                        <span className="legend__value">
                          {formatNumber(row.count)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            <Card
              title="Findings by OWASP category"
              subtitle="OWASP API Security Top 10 (2023)"
            >
              {categoryRows.length === 0 ? (
                <EmptyState
                  icon="layers"
                  title="No categories to chart"
                  text="Categories appear once a scan produces findings."
                />
              ) : (
                <div className="chart-frame">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={categoryRows}
                      layout="vertical"
                      margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--chart-grid)"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        allowDecimals={false}
                        tick={{ fontSize: 11, fill: "var(--chart-axis)" }}
                        stroke="var(--chart-grid)"
                      />
                      <YAxis
                        type="category"
                        dataKey="short"
                        width={56}
                        tick={{ fontSize: 11, fill: "var(--chart-axis)" }}
                        stroke="var(--chart-grid)"
                      />
                      <Tooltip
                        contentStyle={TOOLTIP_STYLE}
                        itemStyle={{ color: "var(--chart-ink)" }}
                        labelStyle={{ color: "var(--chart-ink)" }}
                        formatter={(value) => [
                          formatNumber(Number(value)),
                          "Findings",
                        ]}
                        labelFormatter={(label) =>
                          labelByShort.get(String(label)) ?? String(label)
                        }
                      />
                      <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={16}>
                        {categoryRows.map((row, index) => (
                          <Cell
                            key={row.code}
                            fill={SERIES_COLORS[index % SERIES_COLORS.length]}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </div>

          <Card
            title="Recent scans"
            subtitle={`${formatNumber(data.recent_scans.length)} most recent`}
            flush
            actions={
              <Link className="btn btn--ghost btn--sm" to="/projects">
                All projects
                <Icon name="chevron-right" size={14} />
              </Link>
            }
          >
            {data.recent_scans.length === 0 ? (
              <EmptyState
                icon="activity"
                title="No scans yet"
                text="Open a target and run a scan; progress and results show up here."
              />
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Target</th>
                      <th>Status</th>
                      <th>Highest severity</th>
                      <th>Started</th>
                      <th className="is-actions">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_scans.map((scan) => (
                      <tr key={scan.id}>
                        <td>
                          <Link
                            className="strong"
                            to={`/targets/${scan.target_id}`}
                          >
                            {scan.target_name}
                          </Link>
                          <div className="tiny subtle">Scan #{scan.id}</div>
                        </td>
                        <td>
                          <StatusBadge status={scan.status} />
                        </td>
                        <td>
                          {scan.top_finding !== null ? (
                            <span className="row">
                              <SeverityBadge
                                severity={scan.top_finding.severity}
                              />
                              <span className="small muted truncate">
                                {scan.top_finding.title}
                              </span>
                            </span>
                          ) : (
                            <Badge outline>No findings</Badge>
                          )}
                        </td>
                        <td className="small muted">
                          {formatRelative(scan.started_at)}
                        </td>
                        <td className="is-actions">
                          <Link
                            className="btn btn--secondary btn--sm"
                            to={`/targets/${scan.target_id}/scans/${scan.id}`}
                          >
                            View findings
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
