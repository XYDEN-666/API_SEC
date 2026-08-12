import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  createCredential,
  createTarget,
  getProject,
  importOpenApi,
  listCredentials,
  listEndpoints,
  listTargets,
  type Credential,
  type Endpoint,
  type ImportOpenApiResult,
  type Project,
  type Target,
} from "../api/client";

export default function ProjectDetail() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const [project, setProject] = useState<Project | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(
    null,
  );
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [importResult, setImportResult] =
    useState<ImportOpenApiResult | null>(null);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [identityName, setIdentityName] = useState("");
  const [authType, setAuthType] = useState("api_key");
  const [credentialValue, setCredentialValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (Number.isNaN(id)) {
      setError("Invalid project id");
      setLoading(false);
      return;
    }
    Promise.all([getProject(id), listTargets(id)])
      .then(([projectData, targetData]) => {
        setProject(projectData);
        setTargets(targetData);
        if (targetData.length > 0) {
          setSelectedTargetId(targetData[0].id);
        }
      })
      .catch((err: unknown) =>
        setError(
          err instanceof Error ? err.message : "Failed to load project data",
        ),
      )
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (selectedTargetId === null) {
      return;
    }
    Promise.all([
      listEndpoints(selectedTargetId),
      listCredentials(selectedTargetId),
    ])
      .then(([endpointData, credentialData]) => {
        setEndpoints(endpointData);
        setCredentials(credentialData);
        setError(null);
      })
      .catch((err: unknown) =>
        setError(
          err instanceof Error ? err.message : "Failed to load target data",
        ),
      );
  }, [selectedTargetId]);

  async function refreshEndpoints() {
    if (selectedTargetId === null) {
      return;
    }
    setEndpoints(await listEndpoints(selectedTargetId));
  }

  async function refreshCredentials() {
    if (selectedTargetId === null) {
      return;
    }
    setCredentials(await listCredentials(selectedTargetId));
  }

  async function handleTargetSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const target = await createTarget(id, name, baseUrl);
      setTargets([...targets, target]);
      setName("");
      setBaseUrl("");
      setSelectedTargetId(target.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create target");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleImport(event: FormEvent) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file || selectedTargetId === null) {
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const result = await importOpenApi(selectedTargetId, file);
      setImportResult(result);
      await refreshEndpoints();
      if (fileRef.current) {
        fileRef.current.value = "";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import spec");
    } finally {
      setUploading(false);
    }
  }

  async function handleCredentialSubmit(event: FormEvent) {
    event.preventDefault();
    if (selectedTargetId === null) {
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await createCredential(selectedTargetId, identityName, authType, credentialValue);
      setIdentityName("");
      setCredentialValue("");
      await refreshCredentials();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to add credential",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <p>
        <Link to="/projects">← Back to projects</Link>
      </p>
      <h2>{project ? project.name : `Project #${id}`}</h2>

      {error !== null && <p role="alert">{error}</p>}

      <h3>Targets</h3>
      <form onSubmit={handleTargetSubmit}>
        <label>
          Target name
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Target name"
            required
            maxLength={255}
          />
        </label>
        <label>
          Base URL
          <input
            type="text"
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
            placeholder="https://api.example.com"
            required
            maxLength={2048}
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Adding…" : "Add target"}
        </button>
      </form>

      {loading ? (
        <p>Loading…</p>
      ) : targets.length === 0 ? (
        <p>No targets yet — add one above.</p>
      ) : (
        <label>
          Managing target
          <select
            name="target"
            value={selectedTargetId ?? undefined}
            onChange={(event) =>
              setSelectedTargetId(Number(event.target.value))
            }
          >
            {targets.map((target) => (
              <option key={target.id} value={target.id}>
                {target.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {selectedTargetId !== null && (
        <>
          <h3>Import OpenAPI</h3>
          <form onSubmit={handleImport}>
            <input
              type="file"
              ref={fileRef}
              accept=".json,.yaml,.yml,application/json,application/yaml"
              required
            />
            <button type="submit" disabled={uploading}>
              {uploading ? "Uploading…" : "Upload spec"}
            </button>
          </form>
          {importResult !== null && (
            <p>
              {importResult.message} ({importResult.endpoints_count} endpoints)
            </p>
          )}

          <h3>Endpoints</h3>
          {endpoints.length === 0 ? (
            <p>No endpoints yet — import an OpenAPI spec above.</p>
          ) : (
            <ul>
              {endpoints.map((endpoint) => (
                <li key={endpoint.id}>
                  <strong>{endpoint.method}</strong> {endpoint.path}
                </li>
              ))}
            </ul>
          )}

          <h3>Credentials</h3>
          <form onSubmit={handleCredentialSubmit}>
            <label>
              Identity name
              <input
                type="text"
                value={identityName}
                onChange={(event) => setIdentityName(event.target.value)}
                placeholder="Identity name"
                required
                maxLength={255}
              />
            </label>
            <label>
              Auth type
              <select
                name="auth_type"
                value={authType}
                onChange={(event) => setAuthType(event.target.value)}
              >
                <option value="api_key">API key</option>
                <option value="bearer">Bearer token</option>
                <option value="basic">Basic auth</option>
              </select>
            </label>
            <label>
              Secret value
              <input
                type="password"
                value={credentialValue}
                onChange={(event) => setCredentialValue(event.target.value)}
                placeholder="Secret value"
                required
                maxLength={4096}
              />
            </label>
            <button type="submit" disabled={submitting}>
              {submitting ? "Adding…" : "Add credential"}
            </button>
          </form>
          {credentials.length === 0 ? (
            <p>No credentials yet.</p>
          ) : (
            <ul>
              {credentials.map((credential) => (
                <li key={credential.id}>
                  {credential.identity_name} ({credential.auth_type}) —{" "}
                  {credential.masked_value}
                </li>
              ))}
            </ul>
          )}

          <h3>Scan</h3>
          <p>
            <Link to={`/targets/${selectedTargetId}/results`}>
              View scan results for this target
            </Link>
          </p>
        </>
      )}
    </section>
  );
}
