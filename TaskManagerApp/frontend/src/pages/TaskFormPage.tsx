import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, apiError } from "../api/client";
import { TASK_STATUSES, type Task, type TaskStatus, type User } from "../types";

const EMPTY = {
  title: "",
  description: "",
  deadline: "",
  status: "pending" as TaskStatus,
  assigned_user_id: "",
};

export default function TaskFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [form, setForm] = useState(EMPTY);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(isEdit);

  useEffect(() => {
    api.get<User[]>("/api/users").then((res) => setUsers(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isEdit) return;
    api
      .get<Task>(`/api/tasks/${id}`)
      .then((res) => {
        const t = res.data;
        if (!t.can_edit) {
          navigate("/", { replace: true });
          return;
        }
        setForm({
          title: t.title,
          description: t.description,
          deadline: t.deadline,
          status: t.status,
          assigned_user_id: String(t.assigned_user_id),
        });
      })
      .catch(() => navigate("/", { replace: true }))
      .finally(() => setLoading(false));
  }, [id, isEdit, navigate]);

  const set =
    (key: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const payload = {
      title: form.title,
      description: form.description,
      deadline: form.deadline,
      status: form.status,
      assigned_user_id: Number(form.assigned_user_id),
    };
    try {
      if (isEdit) {
        await api.patch(`/api/tasks/${id}`, payload);
      } else {
        await api.post("/api/tasks", payload);
      }
      navigate("/");
    } catch (err) {
      setError(apiError(err, "Could not save the task."));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    if (!confirm("Delete this task? This cannot be undone.")) return;
    setBusy(true);
    try {
      await api.delete(`/api/tasks/${id}`);
      navigate("/");
    } catch (err) {
      setError(apiError(err, "Could not delete the task."));
      setBusy(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-400">Loading…</p>;
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-semibold text-slate-900">
        {isEdit ? "Edit task" : "New task"}
      </h1>

      <form
        onSubmit={onSubmit}
        className="mt-6 space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200"
      >
        <Field label="Title">
          <input className="input" value={form.title} onChange={set("title")} required />
        </Field>

        <Field label="Description">
          <textarea
            className="input min-h-24"
            value={form.description}
            onChange={set("description")}
            required
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Deadline">
            <input type="date" className="input" value={form.deadline} onChange={set("deadline")} required />
          </Field>
          <Field label="Status">
            <select className="input capitalize" value={form.status} onChange={set("status")}>
              {TASK_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Assign to">
          <select className="input" value={form.assigned_user_id} onChange={set("assigned_user_id")} required>
            <option value="">Select a user…</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name}
              </option>
            ))}
          </select>
        </Field>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <div className="flex items-center justify-between pt-2">
          <div className="flex gap-2">
            <button type="submit" disabled={busy} className="btn-primary">
              {busy ? "Saving…" : isEdit ? "Save changes" : "Create task"}
            </button>
            <button type="button" onClick={() => navigate("/")} className="btn-secondary">
              Cancel
            </button>
          </div>
          {isEdit && (
            <button
              type="button"
              onClick={onDelete}
              disabled={busy}
              className="text-sm font-medium text-rose-600 hover:underline"
            >
              Delete
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
    </label>
  );
}
