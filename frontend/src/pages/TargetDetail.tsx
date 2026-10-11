import { type DragEvent, type FormEvent, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  createCredential,
  deleteCredential,
  deleteTarget,
  getProject,
  getTarget,
  importOpenApi,
  listAuthorizationRecords,
  listCredentials,
  listEndpoints,
  listScans,
  startScan,
  updateTarget,
  type Credential,
  type ImportOpenApiResult,
} from "../api/client";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import {
  MethodBadge,
  StatusBadge,
  default as Badge,
} from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Card, { StatCard } from "../components/ui/Card";
import {
  EmptyState,
  ErrorAlert,
  InfoAlert,
  SkeletonList,
} from "../components/ui/Feedback";
import { Field, PasswordInput, SelectInput, TextInput } from "../components/ui/Field";
import Modal, { ConfirmDialog } from "../components/ui/Modal";
import Tabs from "../components/ui/Tabs";
import { useToast } from "../components/ui/Toaster";
import { useAsyncData } from "../hooks/useAsyncData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { isScanFinished, validateBaseUrl } from "../lib/domain";
import { formatDateTime, formatDuration, formatRelative, pluralize } from "../lib/format";

const POLL_INTERVAL_MS = 2500;
const POLL_TIMEOUT_MS = 180_000;

const AUTH_TYPES = [
  { value: "api_key", label: "API key" },
  { value: "bearer", label: "Bearer token" },
  { value: "basic", label: "Basic auth" },
];

type TabId = "endpoints" | "credentials" | "scans";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export default function TargetDetail() {
  const { targetId } = useParams();
  const id = Number(targetId);
  const navigate = useNavigate();
  const toast = useToast();

  const target = useAsyncData(() => getTarget(id), [id], {
    enabled: Number.isFinite(id),
  });
  const projectId = target.data?.project_id;
  const project = useAsyncData(() => getProject(projectId as number), [projectId], {
    enabled: typeof projectId === "number",
  });
  const records = useAsyncData(
    () => listAuthorizationRecords(projectId as number),
    [projectId],
    { enabled: typeof projectId === "number" },
  );
  const endpoints = useAsyncData(() => listEndpoints(id), [id], {
    enabled: Number.isFinite(id),
  });
  const credentials = useAsyncData(() => listCredentials(id), [id], {
    enabled: Number.isFinite(id),
  });
  const scans = useAsyncData(() => listScans(id), [id], {
    enabled: Number.isFinite(id),
  });

  const [tab, setTab] = useState<TabId>("endpoints");
  const [endpointQuery, setEndpointQuery] = useState("");
  const [identityName, setIdentityName] = useState("");
  const [authType, setAuthType] = useState("api_key");
  const [secret, setSecret] = useState("");
  const [credentialError, setCredentialError] = useState<string | null>(null);
  const [pendingCredential, setPendingCredential] = useState<Credential | null>(
    null,
  );
  const [busy, setBusy] = useState(false);

  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editUrl, setEditUrl] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [scanOpen, setScanOpen] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [running, setRunning] = useState(false);

  const [importResult, setImportResult] =
    useState<ImportOpenApiResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useDocumentTitle(target.data?.name ?? "Target");

  const endpointList = endpoints.data ?? [];
  const credentialList = credentials.data ?? [];
  const scanList = scans.data ?? [];
  const recordCount = records.data?.length ?? 0;
  const loadError =
    target.error ?? endpoints.error ?? credentials.error ?? scans.error;

  const filteredEndpoints = endpointList.filter((endpoint) => {
    const query = endpointQuery.trim().toLowerCase();
    if (query === "") {
      return true;
    }
    return (
      endpoint.path.toLowerCase().includes(query) ||
      endpoint.method.toLowerCase().includes(query)
    );
  });

  function reloadAll() {
    target.reload();
    endpoints.reload();
    credentials.reload();
    scans.reload();
    records.reload();
  }

  async function uploadSpec(file: File) {
    setImportError(null);
    setUploading(true);
    try {
      const result = await importOpenApi(id, file);
      setImportResult(result);
      endpoints.reload();
      toast.success(
        "OpenAPI document imported",
        `${result.endpoints_count} endpoints extracted.`,
      );
    } catch (err) {
      setImportResult(null);
      setImportError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setUploading(false);
    }
  }

  function handleFileInput(files: FileList | null) {
    const file = files?.[0];
    if (file !== undefined) {
      void uploadSpec(file);
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    handleFileInput(event.dataTransfer.files);
  }

  async function handleCredentialSubmit(event: FormEvent) {
    event.preventDefault();
    if (identityName.trim() === "" || secret === "") {
      setCredentialError("Identity name and secret are both required.");
      return;
    }
    setBusy(true);
    setCredentialError(null);
    try {
      const created = await createCredential(
        id,
        identityName.trim(),
        authType,
        secret,
      );
      credentials.setData([...credentialList, created]);
      setIdentityName("");
      setSecret("");
      toast.success("Credential stored", "The secret is encrypted at rest.");
    } catch (err) {
      setCredentialError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCredentialDelete() {
    if (pendingCredential === null) {
      return;
    }
    setBusy(true);
    try {
      await deleteCredential(id, pendingCredential.id);
      credentials.setData(
        credentialList.filter((item) => item.id !== pendingCredential.id),
      );
      toast.success("Credential deleted");
      setPendingCredential(null);
    } catch (err) {
      toast.error(
        "Delete failed",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleEditSubmit(event: FormEvent) {
    event.preventDefault();
    const name = editName.trim();
    const urlError = validateBaseUrl(editUrl);
    if (name === "") {
      setEditError("Target name is required.");
      return;
    }
    if (urlError !== null) {
      setEditError(urlError);
      return;
    }
    setBusy(true);
    setEditError(null);
    try {
      const updated = await updateTarget(id, name, editUrl.trim());
      target.setData(updated);
      setEditOpen(false);
      toast.success("Target updated");
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteTarget() {
    setBusy(true);
    try {
      await deleteTarget(id);
      toast.success("Target deleted");
      navigate(`/projects/${projectId ?? ""}`);
    } catch (err) {
      toast.error(
        "Delete failed",
        err instanceof Error ? err.message : undefined,
      );
      setBusy(false);
    }
  }

  async function handleRunScan() {
    setScanOpen(false);
    setRunning(true);
    try {
      const queued = await startScan(id);
      toast.info("Scan queued", "Scanners are running in the background.");
      const deadline = Date.now() + POLL_TIMEOUT_MS;
      while (Date.now() < deadline) {
        await sleep(POLL_INTERVAL_MS);
        const latest = await listScans(id);
        scans.setData(latest);
        // Watch the scan we queued: an older, already-finished scan must never
        // be mistaken for this run while the worker is still picking it up.
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

  if (!Number.isFinite(id)) {
    return (
      <div className="page">
        <ErrorAlert title="Invalid target">
          The target id in the URL is not a number.
        </ErrorAlert>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title={target.data?.name ?? `Target #${id}`}
        subtitle={
          target.data !== null ? (
            <span className="row">
              <span className="mono break-all">{target.data.base_url}</span>
            </span>
          ) : undefined
        }
        breadcrumbs={[
          { label: "Projects", to: "/projects" },
          project.data !== null
            ? { label: project.data.name, to: `/projects/${project.data.id}` }
            : { label: "Project" },
          { label: target.data?.name ?? `Target #${id}` },
        ]}
        actions={
          <>
            <Button
              icon={<Icon name="edit" size={16} />}
              onClick={() => {
                setEditName(target.data?.name ?? "");
                setEditUrl(target.data?.base_url ?? "");
                setEditError(null);
                setEditOpen(true);
              }}
            >
              Edit
            </Button>
            <Button
              variant="danger"
              icon={<Icon name="trash" size={16} />}
              onClick={() => setDeleteOpen(true)}
            >
              Delete
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
              {running ? "Scanning…" : "Run scan"}
            </Button>
          </>
        }
      />

      {loadError !== null && (
        <ErrorAlert action={<Button onClick={reloadAll}>Try again</Button>}>
          {loadError}
        </ErrorAlert>
      )}

      {target.loading && target.data === null && <SkeletonList rows={2} />}

      <div className="grid grid--4">
        <StatCard
          label="Endpoints"
          value={endpointList.length}
          icon={<Icon name="list" size={20} />}
        />
        <StatCard
          label="Identities"
          value={credentialList.length}
          icon={<Icon name="key" size={20} />}
          tone="info"
        />
        <StatCard
          label="Scans"
          value={scanList.length}
          icon={<Icon name="activity" size={20} />}
          tone="success"
        />
        <StatCard
          label="Authorization records"
          value={recordCount}
          icon={<Icon name="shield-check" size={20} />}
          tone={recordCount === 0 ? "warning" : "success"}
          hint={recordCount === 0 ? "None on file for this project" : undefined}
        />
      </div>

      {recordCount === 0 && project.data !== null && (
        <InfoAlert tone="warning" title="No authorization on file">
          This project has no authorization record. Scanners send live requests
          to <span className="mono">{target.data?.base_url}</span> — record the
          engagement scope first.{" "}
          <Link to={`/projects/${project.data.id}?tab=authorization`}>
            Add a record
          </Link>
          .
        </InfoAlert>
      )}

      <Card
        title="OpenAPI import"
        subtitle="Upload the OpenAPI 3.x document (JSON or YAML). Importing replaces this target's extracted endpoints."
      >
        {importError !== null && (
          <ErrorAlert title="Import failed">{importError}</ErrorAlert>
        )}
        <div
          className={`dropzone${dragging ? " is-dragging" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          <span className="dropzone__icon">
            <Icon name="upload" size={18} />
          </span>
          <div className="stack stack--sm">
            <span className="strong">Drop an OpenAPI 3.x file here</span>
            <span className="small muted">JSON or YAML, up to a few MB</span>
          </div>
          <div className="row">
            <Button
              onClick={() => fileRef.current?.click()}
              loading={uploading}
              icon={<Icon name="file" size={16} />}
            >
              {uploading ? "Uploading…" : "Choose file"}
            </Button>
            {importResult !== null && (
              <span className="small subtle">
                Last import: {importResult.title ?? "untitled"}{" "}
                {importResult.version !== null && `v${importResult.version}`}
              </span>
            )}
          </div>
          <input
            ref={fileRef}
            className="file-input"
            type="file"
            accept=".json,.yaml,.yml,application/json,application/x-yaml"
            onChange={(event) => {
              handleFileInput(event.target.files);
              event.target.value = "";
            }}
          />
        </div>

        {importResult !== null && (
          <dl className="def-list">
            <dt>Document</dt>
            <dd>
              {importResult.title ?? "Untitled"}{" "}
              {importResult.version !== null && (
                <Badge outline>v{importResult.version}</Badge>
              )}
            </dd>
            <dt>OpenAPI version</dt>
            <dd>{importResult.openapi}</dd>
            <dt>Paths</dt>
            <dd>{importResult.paths_count}</dd>
            <dt>Endpoints extracted</dt>
            <dd>{importResult.endpoints_count}</dd>
          </dl>
        )}
      </Card>

      <Tabs
        active={tab}
        onChange={(next) => setTab(next as TabId)}
        tabs={[
          { id: "endpoints", label: "Endpoints", count: endpointList.length },
          {
            id: "credentials",
            label: "Credentials",
            count: credentialList.length,
          },
          { id: "scans", label: "Scans", count: scanList.length },
        ]}
      />

      {tab === "endpoints" && (
        <Card
          title="Imported endpoints"
          subtitle={pluralize(endpointList.length, "operation")}
          flush
          actions={
            endpointList.length > 0 ? (
              <div className="search">
                <span className="search__icon">
                  <Icon name="search" size={15} />
                </span>
                <TextInput
                  value={endpointQuery}
                  onChange={(event) => setEndpointQuery(event.target.value)}
                  placeholder="Filter path or method"
                  aria-label="Filter endpoints"
                />
              </div>
            ) : undefined
          }
        >
          {endpointList.length === 0 ? (
            <EmptyState
              icon="file"
              title="No endpoints imported"
              text="Upload the target's OpenAPI 3.x document above; each path and method becomes a scannable endpoint."
            />
          ) : filteredEndpoints.length === 0 ? (
            <EmptyState
              icon="search"
              title="No matching endpoints"
              text={`Nothing matches “${endpointQuery}”.`}
              action={
                <Button onClick={() => setEndpointQuery("")}>Clear filter</Button>
              }
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Path</th>
                    <th>Parameters</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEndpoints.map((endpoint) => (
                    <tr key={endpoint.id}>
                      <td>
                        <MethodBadge method={endpoint.method} />
                      </td>
                      <td>
                        <span className="mono small break-all">
                          {endpoint.path}
                        </span>
                      </td>
                      <td className="small muted">
                        {endpoint.parameters === null ||
                        endpoint.parameters.length === 0 ? (
                          "—"
                        ) : (
                          <span className="row row--wrap">
                            {endpoint.parameters.slice(0, 4).map((parameter, index) => (
                              <Badge
                                key={`${endpoint.id}-${index}`}
                                outline
                                mono
                              >
                                {parameter.name ?? "param"}
                                {parameter.in !== undefined &&
                                  ` · ${parameter.in}`}
                              </Badge>
                            ))}
                            {endpoint.parameters.length > 4 && (
                              <span className="tiny subtle">
                                +{endpoint.parameters.length - 4} more
                              </span>
                            )}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === "credentials" && (
        <div className="grid grid--2">
          <Card
            title="Add an identity"
            subtitle="Secrets are encrypted at rest and only ever returned masked."
          >
            <form className="form" onSubmit={handleCredentialSubmit} noValidate>
              <Field label="Identity name" hint="e.g. tenant-a / low-privilege user">
                {({ id: fieldId }) => (
                  <TextInput
                    id={fieldId}
                    value={identityName}
                    onChange={(event) => setIdentityName(event.target.value)}
                    placeholder="tenant-a"
                    maxLength={255}
                    required
                  />
                )}
              </Field>
              <Field label="Auth type">
                {({ id: fieldId }) => (
                  <SelectInput
                    id={fieldId}
                    value={authType}
                    onChange={(event) => setAuthType(event.target.value)}
                  >
                    {AUTH_TYPES.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </SelectInput>
                )}
              </Field>
              <Field
                label="Secret value"
                hint="Never returned by the API"
                error={credentialError}
              >
                {({ id: fieldId, invalid }) => (
                  <PasswordInput
                    id={fieldId}
                    value={secret}
                    invalid={invalid}
                    onChange={(event) => setSecret(event.target.value)}
                    placeholder="Paste the token or key"
                    maxLength={4096}
                    autoComplete="off"
                    required
                  />
                )}
              </Field>
              <Button
                type="submit"
                variant="primary"
                loading={busy}
                icon={<Icon name="plus" size={16} />}
              >
                Store credential
              </Button>
            </form>
          </Card>

          <Card
            title="Stored identities"
            subtitle={pluralize(credentialList.length, "identity", "identities")}
            flush
          >
            {credentialList.length === 0 ? (
              <EmptyState
                icon="key"
                title="No credentials yet"
                text="Multi-identity credentials let the IDOR/BOLA scanner replay each endpoint as several users."
              />
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Identity</th>
                      <th>Type</th>
                      <th>Value</th>
                      <th className="is-actions" />
                    </tr>
                  </thead>
                  <tbody>
                    {credentialList.map((credential) => (
                      <tr key={credential.id}>
                        <td className="strong">{credential.identity_name}</td>
                        <td>
                          <Badge outline>{credential.auth_type}</Badge>
                        </td>
                        <td className="mono small">{credential.masked_value}</td>
                        <td className="is-actions">
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            title="Delete credential"
                            aria-label={`Delete ${credential.identity_name}`}
                            onClick={() => setPendingCredential(credential)}
                            icon={<Icon name="trash" size={15} />}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {tab === "scans" && (
        <Card
          title="Scan history"
          subtitle={
            running
              ? "A scan is running — results will open automatically."
              : "Each scan is stored with its findings and evidence."
          }
          actions={
            <Button
              size="sm"
              variant="primary"
              loading={running}
              onClick={() => {
                setAcknowledged(false);
                setScanOpen(true);
              }}
              icon={<Icon name="play" size={15} />}
            >
              {running ? "Scanning…" : "Run scan"}
            </Button>
          }
          flush
        >
          {scanList.length === 0 ? (
            <EmptyState
              icon="activity"
              title="No scans yet"
              text="Import an OpenAPI document, then run a scan. Six scanners run per endpoint and results are deduplicated."
              action={
                <Button
                  variant="primary"
                  onClick={() => {
                    setAcknowledged(false);
                    setScanOpen(true);
                  }}
                  disabled={endpointList.length === 0}
                >
                  Run scan
                </Button>
              }
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Scan</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Duration</th>
                    <th className="is-actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {scanList.map((scan) => (
                    <tr key={scan.id}>
                      <td className="strong">#{scan.id}</td>
                      <td>
                        <StatusBadge status={scan.status} />
                      </td>
                      <td className="small muted" title={formatDateTime(scan.started_at)}>
                        {formatRelative(scan.started_at)}
                      </td>
                      <td className="small muted">
                        {formatDuration(scan.started_at, scan.finished_at) ?? "—"}
                      </td>
                      <td className="is-actions">
                        <Link
                          className="btn btn--secondary btn--sm"
                          to={`/targets/${id}/scans/${scan.id}`}
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
              disabled={!acknowledged || endpointList.length === 0}
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
        <dl className="def-list">
          <dt>Target</dt>
          <dd>{target.data?.name}</dd>
          <dt>Base URL</dt>
          <dd className="mono break-all">{target.data?.base_url}</dd>
          <dt>Endpoints</dt>
          <dd>{endpointList.length}</dd>
          <dt>Scanners</dt>
          <dd>
            headers, cors, http_methods, jwt, sqli_indicators, idor_bola
          </dd>
        </dl>
        {endpointList.length === 0 && (
          <InfoAlert tone="warning" title="Nothing to scan">
            Import an OpenAPI document first so the scanners have endpoints to
            probe.
          </InfoAlert>
        )}
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
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Edit target"
        footer={
          <>
            <Button
              type="submit"
              form="target-edit-form"
              variant="primary"
              loading={busy}
            >
              Save changes
            </Button>
            <Button variant="ghost" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
          </>
        }
      >
        <form
          id="target-edit-form"
          className="form"
          onSubmit={handleEditSubmit}
          noValidate
        >
          <Field label="Target name">
            {({ id: fieldId }) => (
              <TextInput
                id={fieldId}
                value={editName}
                onChange={(event) => setEditName(event.target.value)}
                maxLength={255}
                required
              />
            )}
          </Field>
          <Field label="Base URL" error={editError}>
            {({ id: fieldId, invalid }) => (
              <TextInput
                id={fieldId}
                value={editUrl}
                invalid={invalid}
                onChange={(event) => setEditUrl(event.target.value)}
                maxLength={2048}
                required
              />
            )}
          </Field>
        </form>
      </Modal>

      <ConfirmDialog
        open={pendingCredential !== null}
        title="Delete credential"
        tone="danger"
        confirmLabel="Delete credential"
        busy={busy}
        message={
          <p>
            The stored secret for{" "}
            <strong>{pendingCredential?.identity_name}</strong> will be removed;
            existing findings keep their evidence.
          </p>
        }
        onConfirm={() => void handleCredentialDelete()}
        onCancel={() => setPendingCredential(null)}
      />

      <ConfirmDialog
        open={deleteOpen}
        title="Delete target"
        tone="danger"
        confirmLabel="Delete target"
        busy={busy}
        message={
          <p>
            Deleting <strong>{target.data?.name}</strong> removes its endpoints,
            credentials, scans and findings. This cannot be undone.
          </p>
        }
        onConfirm={() => void handleDeleteTarget()}
        onCancel={() => setDeleteOpen(false)}
      />
    </div>
  );
}
