import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createProject,
  deleteProject,
  listProjects,
  updateProject,
  type Project,
} from "../api/client";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import { EmptyState, ErrorAlert, SkeletonList } from "../components/ui/Feedback";
import { Field, TextInput } from "../components/ui/Field";
import Modal, { ConfirmDialog } from "../components/ui/Modal";
import { useToast } from "../components/ui/Toaster";
import { useAsyncData } from "../hooks/useAsyncData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDate, pluralize } from "../lib/format";

interface EditorState {
  mode: "create" | "rename";
  project: Project | null;
}

export default function Projects() {
  const navigate = useNavigate();
  const toast = useToast();
  const projects = useAsyncData(() => listProjects(), []);
  const [query, setQuery] = useState("");
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null);

  useDocumentTitle("Projects");

  const list = projects.data ?? [];
  const filtered = list.filter((project) =>
    project.name.toLowerCase().includes(query.trim().toLowerCase()),
  );

  function openCreate() {
    setName("");
    setFormError(null);
    setEditor({ mode: "create", project: null });
  }

  function openRename(project: Project) {
    setName(project.name);
    setFormError(null);
    setEditor({ mode: "rename", project });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (editor === null) {
      return;
    }
    const trimmed = name.trim();
    if (trimmed === "") {
      setFormError("Project name is required.");
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      if (editor.mode === "create") {
        const created = await createProject(trimmed);
        projects.setData([...list, created]);
        setEditor(null);
        toast.success("Project created", `“${created.name}” is ready.`);
        navigate(`/projects/${created.id}`);
      } else if (editor.project !== null) {
        const updated = await updateProject(editor.project.id, trimmed);
        projects.setData(
          list.map((item) => (item.id === updated.id ? updated : item)),
        );
        setEditor(null);
        toast.success("Project renamed");
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (pendingDelete === null) {
      return;
    }
    setBusy(true);
    try {
      await deleteProject(pendingDelete.id);
      projects.setData(list.filter((item) => item.id !== pendingDelete.id));
      toast.success("Project deleted", `“${pendingDelete.name}” was removed.`);
      setPendingDelete(null);
    } catch (err) {
      toast.error(
        "Could not delete project",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <PageHeader
        title="Projects"
        subtitle="Each project groups the targets and authorization records for one engagement."
        actions={
          <Button
            variant="primary"
            onClick={openCreate}
            icon={<Icon name="plus" size={16} />}
          >
            New project
          </Button>
        }
      />

      {projects.error !== null && (
        <ErrorAlert action={<Button onClick={projects.reload}>Try again</Button>}>
          {projects.error}
        </ErrorAlert>
      )}

      {projects.loading && projects.data === null && <SkeletonList rows={3} />}

      {projects.data !== null && (
        <Card
          title="All projects"
          subtitle={pluralize(list.length, "project")}
          actions={
            list.length > 0 ? (
              <div className="search">
                <span className="search__icon">
                  <Icon name="search" size={15} />
                </span>
                <TextInput
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Filter by name"
                  aria-label="Filter projects by name"
                />
              </div>
            ) : undefined
          }
          flush
        >
          {list.length === 0 ? (
            <EmptyState
              icon="folder"
              title="No projects yet"
              text="Create a project to hold the targets you are authorised to assess."
              action={
                <Button
                  variant="primary"
                  onClick={openCreate}
                  icon={<Icon name="plus" size={16} />}
                >
                  New project
                </Button>
              }
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon="search"
              title="No matches"
              text={`Nothing matches “${query}”.`}
              action={
                <Button onClick={() => setQuery("")}>Clear filter</Button>
              }
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Created</th>
                    <th className="is-actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((project) => (
                    <tr key={project.id}>
                      <td>
                        <Link className="strong" to={`/projects/${project.id}`}>
                          {project.name}
                        </Link>
                        <div className="tiny subtle">Project #{project.id}</div>
                      </td>
                      <td className="small muted">
                        {formatDate(project.created_at)}
                      </td>
                      <td className="is-actions">
                        <div className="row row--end">
                          <Link
                            className="btn btn--secondary btn--sm"
                            to={`/projects/${project.id}`}
                          >
                            Open
                          </Link>
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            aria-label={`Rename ${project.name}`}
                            title="Rename"
                            onClick={() => openRename(project)}
                            icon={<Icon name="edit" size={15} />}
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            aria-label={`Delete ${project.name}`}
                            title="Delete"
                            onClick={() => setPendingDelete(project)}
                            icon={<Icon name="trash" size={15} />}
                          />
                        </div>
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
        open={editor !== null}
        onClose={() => setEditor(null)}
        title={editor?.mode === "rename" ? "Rename project" : "New project"}
        subtitle="Use a name that identifies the engagement or product."
        footer={
          <>
            <Button
              type="submit"
              form="project-form"
              variant="primary"
              loading={busy}
            >
              {editor?.mode === "rename" ? "Save changes" : "Create project"}
            </Button>
            <Button variant="ghost" onClick={() => setEditor(null)} disabled={busy}>
              Cancel
            </Button>
          </>
        }
      >
        <form
          id="project-form"
          className="form"
          onSubmit={handleSubmit}
          noValidate
        >
          <Field label="Project name" error={formError}>
            {({ id, invalid }) => (
              <TextInput
                id={id}
                value={name}
                invalid={invalid}
                onChange={(event) => setName(event.target.value)}
                placeholder="Checkout API"
                maxLength={255}
                autoFocus
                required
              />
            )}
          </Field>
          <button type="submit" className="sr-only">
            Submit
          </button>
        </form>
      </Modal>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete project"
        tone="danger"
        confirmLabel="Delete project"
        busy={busy}
        message={
          <p>
            Deleting <strong>{pendingDelete?.name}</strong> also removes its
            targets, endpoints, credentials, scans and findings. This cannot be
            undone.
          </p>
        }
        onConfirm={() => void handleDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
