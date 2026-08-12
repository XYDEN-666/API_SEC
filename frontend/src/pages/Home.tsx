import { useEffect, useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAuth } from "../auth/AuthContext";
import { getDashboardSummary, type DashboardSummary } from "../api/client";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];
const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};
const SEVERITY_COLORS: Record<string, string> = {
  critical: "#b91c1c",
  high: "#ea580c",
  medium: "#d97706",
  low: "#16a34a",
  info: "#64748b",
};
const CATEGORY_COLORS = [
  "#2563eb",
  "#7c3aed",
  "#0891b2",
  "#db2777",
  "#65a30d",
  "#ea580c",
  "#0d9488",
  "#4f46e5",
  "#b45309",
  "#be123c",
];

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function Home() {
  const { user, logout } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch((err: unknown) =>
        setError(
          err instanceof Error ? err.message : "Failed to load dashboard",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  const severityData = SEVERITY_ORDER.map((severity) => ({
    name: SEVERITY_LABELS[severity],
    value: summary?.findings_by_severity[severity] ?? 0,
  }));
  const categoryData = summary
    ? Object.entries(summary.findings_by_category).map(
        ([code, count]) => ({ name: code, count }),
      )
    : [];

  const cards = [
    { label: "Projects", value: summary?.total_projects ?? 0 },
    { label: "Targets", value: summary?.total_targets ?? 0 },
    { label: "Scans run", value: summary?.total_scans ?? 0 },
    { label: "Findings", value: summary?.total_findings ?? 0 },
  ];

  return (
    <section>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <h2>Dashboard</h2>
        <p>
          {user !== null && <>Signed in as {user.email} · </>}
          <button type="button" onClick={logout}>
            Log out
          </button>
        </p>
      </div>

      {error !== null && <p role="alert">{error}</p>}
      {loading && <p>Loading…</p>}

      {!loading && summary !== null && (
        <>
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            {cards.map((card) => (
              <div
                key={card.label}
                style={{
                  border: "1px solid #d1d5db",
                  borderRadius: 8,
                  padding: "0.75rem 1.25rem",
                  minWidth: 140,
                }}
              >
                <div style={{ fontSize: "1.75rem", fontWeight: 700 }}>
                  {card.value}
                </div>
                <div>{card.label}</div>
              </div>
            ))}
          </div>

          <h3>Findings by severity</h3>
          {summary.total_findings === 0 ? (
            <p>No findings yet — run a scan to see the breakdown.</p>
          ) : (
            <div style={{ maxWidth: 420 }}>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={severityData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={45}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {severityData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={
                          SEVERITY_COLORS[entry.name.toLowerCase()] ??
                          "#64748b"
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          <h3>Findings by OWASP category</h3>
          {summary.total_findings === 0 ? (
            <p>No findings yet — run a scan to see the breakdown.</p>
          ) : (
            <div style={{ maxWidth: 640 }}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={categoryData}
                  layout="vertical"
                  margin={{ left: 30 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={110}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip />
                  <Bar dataKey="count" name="Findings">
                    {categoryData.map((entry, index) => (
                      <Cell
                        key={entry.name}
                        fill={
                          CATEGORY_COLORS[index % CATEGORY_COLORS.length]
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <h3>Recent scans</h3>
          {summary.recent_scans.length === 0 ? (
            <p>
              No scans yet — create a project, add a target, and run a scan.
            </p>
          ) : (
            <table style={{ borderCollapse: "collapse", minWidth: "40rem" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Target</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Highest severity</th>
                  <th style={thStyle} />
                </tr>
              </thead>
              <tbody>
                {summary.recent_scans.map((scan) => (
                  <tr key={scan.id}>
                    <td style={tdStyle}>{scan.target_name}</td>
                    <td style={tdStyle}>
                      <span
                        className={`badge status-${scan.status}`}
                      >
                        {scan.status}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      {scan.top_finding !== null
                        ? `${capitalize(scan.top_finding.severity)} — ${
                            scan.top_finding.title
                          }`
                        : "—"}
                    </td>
                    <td style={tdStyle}>
                      <Link
                        to={`/targets/${scan.target_id}/results?scan=${scan.id}`}
                      >
                        View findings
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      <style>{`
        .badge.status-completed { color: #166534; background: #dcfce7; }
        .badge.status-completed_with_errors { color: #92400e; background: #fef3c7; }
        .badge.status-running { color: #1e40af; background: #dbeafe; }
        .badge.status-failed { color: #991b1b; background: #fee2e2; }
        .badge.status-queued { color: #374151; background: #e5e7eb; }
      `}</style>
    </section>
  );
}

const thStyle: CSSProperties = {
  borderBottom: "2px solid #d1d5db",
  padding: "0.5rem 0.75rem",
  textAlign: "left",
};

const tdStyle: CSSProperties = {
  borderBottom: "1px solid #e5e7eb",
  padding: "0.5rem 0.75rem",
};
