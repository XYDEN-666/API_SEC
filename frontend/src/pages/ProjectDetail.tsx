import { type FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  createTarget,
  getProject,
  listTargets,
  type Project,
  type Target,
} from "../api/client";

export default function ProjectDetail() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const [project, setProject] = useState<Project | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

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
      })
      .catch((err: unknown) =>
        setError(
          err instanceof Error ? err.message : "Failed to load project data",
        ),
      )
      .finally(() => setLoading(false));
  }, [id]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const target = await createTarget(id, name, baseUrl);
      setTargets([...targets, target]);
      setName("");
      setBaseUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create target");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <p>
        <Link to="/projects">← Back to projects</Link>
      </p>
      <h2>{project ? project.name : `Project #${id}`} — Targets</h2>
      <form onSubmit={handleSubmit}>
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
        {error !== null && <p role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Adding…" : "Add target"}
        </button>
      </form>

      {loading ? (
        <p>Loading…</p>
      ) : targets.length === 0 ? (
        <p>No targets yet.</p>
      ) : (
        <ul>
          {targets.map((target) => (
            <li key={target.id}>
              {target.name} — <code>{target.base_url}</code>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
