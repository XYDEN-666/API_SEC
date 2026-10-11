import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  createAuthorizationRecord,
  createTarget,
  deleteAuthorizationRecord,
  deleteTarget,
  getProject,
  listAuthorizationRecords,
  listTargets,
  updateAuthorizationRecord,
  updateProject,
  updateTarget,
  type AuthorizationRecord,
  type Target,
} from "../api/client";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import Button from "../components/ui/Button";
import Card, { StatCard } from "../components/ui/Card";
import {
  EmptyState,
  ErrorAlert,
  InfoAlert,
  SkeletonList,
} from "../components/ui/Feedback";
import { Field, TextArea, TextInput } from "../components/ui/Field";
import Modal, { ConfirmDialog } from "../components/ui/Modal";
import Tabs from "../components/ui/Tabs";
import { useToast } from "../components/ui/Toaster";
import { useAsyncData } from "../hooks/useAsyncData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { validateBaseUrl } from "../lib/domain";
import { formatDate, pluralize } from "../lib/format";

type TabId = "targets" | "authorization";

interface TargetEditor {
  mode: "create" | "edit";
  target: Target | null;
}

interface RecordEditor {
  mode: "create" | "edit";
  record: AuthorizationRecord | null;
}

export default function ProjectDetail() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const navigate = useNavigate();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // The active tab lives in the URL so it can be linked to directly.
  const tab: TabId =
    searchParams.get("tab") === "authorization" ? "authorization" : "targets";
  const project = useAsyncData(() => getProject(id), [id], {
    enabled: Number.isFinite(id),
  });
  const targets = useAsyncData(() => listTargets(id), [id], {
    enabled: Number.isFinite(id),
  });
  const records = useAsyncData(() => listAuthorizationRecords(id), [id], {
    enabled: Number.isFinite(id),
  });

  const [targetEditor, setTargetEditor] = useState<TargetEditor | null>(null);
  const [targetName, setTargetName] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [targetError, setTargetError] = useState<string | null>(null);

  const [recordEditor, setRecordEditor] = useState<RecordEditor | null>(null);
  const [recordDescription, setRecordDescription] = useState("");
  const [recordScope, setRecordScope] = useState("");
  const [recordError, setRecordError] = useState<string | null>(null);

  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);

  const [pendingTarget, setPendingTarget] = useState<Target | null>(null);
  const [pendingRecord, setPendingRecord] =
    useState<AuthorizationRecord | null>(null);
  const [busy, setBusy] = useState(false);

  useDocumentTitle(project.data?.name ?? "Project");

  const targetList = targets.data ?? [];
  const recordList = records.data ?? [];
  const loadError = project.error ?? targets.error ?? records.error;

  function reloadAll() {
    project.reload();
    targets.reload();
    records.reload();
  }

  function openCreateTarget() {
    setTargetName("");
    setTargetUrl("");
    setTargetError(null);
    setTargetEditor({ mode: "create", target: null });
  }

  function openEditTarget(target: Target) {
    setTargetName(target.name);
    setTargetUrl(target.base_url);
    setTargetError(null);
    setTargetEditor({ mode: "edit", target });
  }

  function openCreateRecord() {
    setRecordDescription("");
    setRecordScope("");
    setRecordError(null);
    setRecordEditor({ mode: "create", record: null });
  }

  function openEditRecord(record: AuthorizationRecord) {
    setRecordDescription(record.description);
    setRecordScope(record.scope_notes ?? "");
    setRecordError(null);
    setRecordEditor({ mode: "edit", record });
  }

  async function handleTargetSubmit(event: FormEvent) {
    event.preventDefault();
    if (targetEditor === null) {
      return;
    }
    const name = targetName.trim();
    const baseUrl = targetUrl.trim();
    if (name === "") {
      setTargetError("Target name is required.");
      return;
    }
    const urlError = validateBaseUrl(baseUrl);
    if (urlError !== null) {
      setTargetError(urlError);
      return;
    }
    setBusy(true);
    setTargetError(null);
    try {
      if (targetEditor.mode === "create") {
        const created = await createTarget(id, name, baseUrl);
        targets.setData([...targetList, created]);
        setTargetEditor(null);
        toast.success("Target added", `“${created.name}” is ready to import.`);
      } else if (targetEditor.target !== null) {
        const updated = await updateTarget(targetEditor.target.id, name, baseUrl);
        targets.setData(
          targetList.map((item) => (item.id === updated.id ? updated : item)),
        );
        setTargetEditor(null);
        toast.success("Target updated");
      }
    } catch (err) {
      setTargetError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRecordSubmit(event: FormEvent) {
    event.preventDefault();
    if (recordEditor === null) {
      return;
    }
    const description = recordDescription.trim();
    const scope = recordScope.trim();
    if (description === "") {
      setRecordError("Describe who authorised this testing.");
      return;
    }
    setBusy(true);
    setRecordError(null);
    try {
      if (recordEditor.mode === "create") {
        const created = await createAuthorizationRecord(
          id,
          description,
          scope === "" ? null : scope,
        );
        records.setData([...recordList, created]);
        setRecordEditor(null);
        toast.success("Authorization record added");
      } else if (recordEditor.record !== null) {
        const updated = await updateAuthorizationRecord(
          recordEditor.record.id,
          description,
          scope === "" ? null : scope,
        );
        records.setData(
          recordList.map((item) => (item.id === updated.id ? updated : item)),
        );
        setRecordEditor(null);
        toast.success("Authorization record updated");
      }
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRename(event: FormEvent) {
    event.preventDefault();
    const name = renameValue.trim();
    if (name === "") {
      setRenameError("Project name is required.");
      return;
    }
    setBusy(true);
    setRenameError(null);
    try {
      const updated = await updateProject(id, name);
      project.setData(updated);
      setRenameOpen(false);
      toast.success("Project renamed");
    } catch (err) {
      setRenameError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    try {
      if (pendingTarget !== null) {
        await deleteTarget(pendingTarget.id);
        targets.setData(targetList.filter((item) => item.id !== pendingTarget.id));
        toast.success("Target deleted", `“${pendingTarget.name}” was removed.`);
        setPendingTarget(null);
      } else if (pendingRecord !== null) {
        await deleteAuthorizationRecord(pendingRecord.id);
        records.setData(
          recordList.filter((item) => item.id !== pendingRecord.id),
        );
        toast.success("Authorization record deleted");
        setPendingRecord(null);
      }
    } catch (err) {
      toast.error(
        "Delete failed",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setBusy(false);
    }
  }

  if (!Number.isFinite(id)) {
    return (
      <div className="page">
        <ErrorAlert title="Invalid project">
          The project id in the URL is not a number.
        </ErrorAlert>
        <div>
          <Link className="btn btn--secondary" to="/projects">
            Back to projects
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title={project.data?.name ?? `Project #${id}`}
        subtitle={
          project.data !== null
            ? `Created ${formatDate(project.data.created_at)} · ${pluralize(
                targetList.length,
                "target",
              )}`
            : undefined
        }
        breadcrumbs={[
          { label: "Projects", to: "/projects" },
          { label: project.data?.name ?? `Project #${id}` },
        ]}
        actions={
          <>
            <Button
              icon={<Icon name="edit" size={16} />}
              onClick={() => {
                setRenameValue(project.data?.name ?? "");
                setRenameError(null);
                setRenameOpen(true);
              }}
            >
              Rename
            </Button>
            <Button
              variant="primary"
              onClick={openCreateTarget}
              icon={<Icon name="plus" size={16} />}
            >
              Add target
            </Button>
          </>
        }
      />

      {loadError !== null && (
        <ErrorAlert action={<Button onClick={reloadAll}>Try again</Button>}>
          {loadError}
        </ErrorAlert>
      )}

      {(project.loading || targets.loading || records.loading) &&
        targets.data === null && <SkeletonList rows={2} />}

      <div className="grid grid--3">
        <StatCard
          label="Targets"
          value={targetList.length}
          icon={<Icon name="target" size={20} />}
        />
        <StatCard
          label="Authorization records"
          value={recordList.length}
          icon={<Icon name="shield-check" size={20} />}
          tone={recordList.length === 0 ? "warning" : "success"}
        />
        <StatCard
          label="Project id"
          value={`#${id}`}
          icon={<Icon name="folder" size={20} />}
          tone="info"
        />
      </div>

      <Tabs
        active={tab}
        onChange={(next) =>
          setSearchParams(next === "targets" ? {} : { tab: next }, {
            replace: true,
          })
        }
        tabs={[
          { id: "targets", label: "Targets", count: targetList.length },
          {
            id: "authorization",
            label: "Authorization",
            count: recordList.length,
          },
        ]}
      />

      {tab === "targets" && (
        <Card
          title="Targets"
          subtitle="APIs in scope for this engagement."
          actions={
            <Button
              size="sm"
              variant="primary"
              onClick={openCreateTarget}
              icon={<Icon name="plus" size={15} />}
            >
              Add target
            </Button>
          }
          flush
        >
          {targetList.length === 0 ? (
            <EmptyState
              icon="target"
              title="No targets yet"
              text="Add the base URL of the API you are authorised to assess, then import its OpenAPI 3.x document."
              action={
                <Button variant="primary" onClick={openCreateTarget}>
                  Add target
                </Button>
              }
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Base URL</th>
                    <th className="is-actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {targetList.map((target) => (
                    <tr key={target.id}>
                      <td>
                        <Link className="strong" to={`/targets/${target.id}`}>
                          {target.name}
                        </Link>
                        <div className="tiny subtle">Target #{target.id}</div>
                      </td>
                      <td>
                        <span className="mono small break-all">
                          {target.base_url}
                        </span>
                      </td>
                      <td className="is-actions">
                        <div className="row row--end">
                          <Link
                            className="btn btn--secondary btn--sm"
                            to={`/targets/${target.id}`}
                          >
                            Open
                          </Link>
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            title="Edit target"
                            aria-label={`Edit ${target.name}`}
                            onClick={() => openEditTarget(target)}
                            icon={<Icon name="edit" size={15} />}
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            title="Delete target"
                            aria-label={`Delete ${target.name}`}
                            onClick={() => setPendingTarget(target)}
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

      {tab === "authorization" && (
        <>
          {recordList.length === 0 && (
            <InfoAlert tone="warning" title="No authorization on file">
              Scanners send real requests to the target. Record who authorised
              this testing and the agreed scope before you run a scan.
            </InfoAlert>
          )}
          <Card
            title="Authorization records"
            subtitle="Evidence that you are permitted to test these targets."
            actions={
              <Button
                size="sm"
                variant="primary"
                onClick={openCreateRecord}
                icon={<Icon name="plus" size={15} />}
              >
                Add record
              </Button>
            }
            flush
          >
            {recordList.length === 0 ? (
              <EmptyState
                icon="shield-check"
                title="Nothing recorded yet"
                text="Example: “Authorised by the platform team under ticket SEC-4821; scope limited to /api/v1.”"
                action={
                  <Button variant="primary" onClick={openCreateRecord}>
                    Add record
                  </Button>
                }
              />
            ) : (
              <div className="stack">
                {recordList.map((record) => (
                  <article className="card" key={record.id}>
                    <div className="card__body card__body--tight">
                      <div className="row row--between">
                        <span className="strong">{record.description}</span>
                        <span className="row">
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            title="Edit record"
                            aria-label="Edit record"
                            onClick={() => openEditRecord(record)}
                            icon={<Icon name="edit" size={15} />}
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            title="Delete record"
                            aria-label="Delete record"
                            onClick={() => setPendingRecord(record)}
                            icon={<Icon name="trash" size={15} />}
                          />
                        </span>
                      </div>
                      {record.scope_notes !== null &&
                        record.scope_notes !== "" && (
                          <p className="small muted">{record.scope_notes}</p>
                        )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Card>
        </>
      )}

      {/* ---- Target editor ---- */}
      <Modal
        open={targetEditor !== null}
        onClose={() => setTargetEditor(null)}
        title={
          targetEditor?.mode === "edit" ? "Edit target" : "Add target"
        }
        subtitle="The base URL is used to resolve every endpoint path from the OpenAPI document."
        footer={
          <>
            <Button
              type="submit"
              form="target-form"
              variant="primary"
              loading={busy}
            >
              {targetEditor?.mode === "edit" ? "Save target" : "Add target"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => setTargetEditor(null)}
              disabled={busy}
            >
              Cancel
            </Button>
          </>
        }
      >
        <form id="target-form" className="form" onSubmit={handleTargetSubmit} noValidate>
          <Field label="Target name">
            {({ id: fieldId }) => (
              <TextInput
                id={fieldId}
                value={targetName}
                onChange={(event) => setTargetName(event.target.value)}
                placeholder="Payments API (staging)"
                maxLength={255}
                required
              />
            )}
          </Field>
          <Field
            label="Base URL"
            hint="http:// or https://"
            error={targetError}
          >
            {({ id: fieldId, invalid }) => (
              <TextInput
                id={fieldId}
                value={targetUrl}
                invalid={invalid}
                onChange={(event) => setTargetUrl(event.target.value)}
                placeholder="https://api.example.com"
                maxLength={2048}
                required
              />
            )}
          </Field>
        </form>
      </Modal>

      {/* ---- Authorization record editor ---- */}
      <Modal
        open={recordEditor !== null}
        onClose={() => setRecordEditor(null)}
        title={
          recordEditor?.mode === "edit"
            ? "Edit authorization record"
            : "Add authorization record"
        }
        subtitle="Kept with the project so the engagement has a paper trail."
        footer={
          <>
            <Button
              type="submit"
              form="record-form"
              variant="primary"
              loading={busy}
            >
              {recordEditor?.mode === "edit" ? "Save record" : "Add record"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => setRecordEditor(null)}
              disabled={busy}
            >
              Cancel
            </Button>
          </>
        }
      >
        <form id="record-form" className="form" onSubmit={handleRecordSubmit} noValidate>
          <Field
            label="Authorization"
            hint="Who approved it?"
            error={recordError}
          >
            {({ id: fieldId, invalid }) => (
              <TextInput
                id={fieldId}
                value={recordDescription}
                invalid={invalid}
                onChange={(event) => setRecordDescription(event.target.value)}
                placeholder="Authorised by the platform team, ticket SEC-4821"
                maxLength={500}
                required
              />
            )}
          </Field>
          <Field label="Scope notes" hint="Optional">
            {({ id: fieldId }) => (
              <TextArea
                id={fieldId}
                value={recordScope}
                onChange={(event) => setRecordScope(event.target.value)}
                placeholder="Testing limited to /api/v1 between 18:00 and 22:00 IST."
                maxLength={5000}
                rows={4}
              />
            )}
          </Field>
        </form>
      </Modal>

      {/* ---- Rename project ---- */}
      <Modal
        open={renameOpen}
        onClose={() => setRenameOpen(false)}
        title="Rename project"
        footer={
          <>
            <Button
              type="submit"
              form="rename-form"
              variant="primary"
              loading={busy}
            >
              Save changes
            </Button>
            <Button
              variant="ghost"
              onClick={() => setRenameOpen(false)}
              disabled={busy}
            >
              Cancel
            </Button>
          </>
        }
      >
        <form id="rename-form" className="form" onSubmit={handleRename} noValidate>
          <Field label="Project name" error={renameError}>
            {({ id: fieldId, invalid }) => (
              <TextInput
                id={fieldId}
                value={renameValue}
                invalid={invalid}
                onChange={(event) => setRenameValue(event.target.value)}
                maxLength={255}
                required
              />
            )}
          </Field>
        </form>
      </Modal>

      <ConfirmDialog
        open={pendingTarget !== null}
        title="Delete target"
        tone="danger"
        confirmLabel="Delete target"
        busy={busy}
        message={
          <p>
            Deleting <strong>{pendingTarget?.name}</strong> removes its imported
            endpoints, credentials, scans and findings.
          </p>
        }
        onConfirm={() => void handleDelete()}
        onCancel={() => setPendingTarget(null)}
      />

      <ConfirmDialog
        open={pendingRecord !== null}
        title="Delete authorization record"
        tone="danger"
        confirmLabel="Delete record"
        busy={busy}
        message={<p>This removes the record from the engagement paper trail.</p>}
        onConfirm={() => void handleDelete()}
        onCancel={() => setPendingRecord(null)}
      />

      <div className="row">
        <Button
          variant="ghost"
          onClick={() => navigate("/projects")}
          icon={<Icon name="arrow-left" size={16} />}
        >
          Back to projects
        </Button>
      </div>
    </div>
  );
}
