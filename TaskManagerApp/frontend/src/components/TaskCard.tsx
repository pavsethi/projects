import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiError } from "../api/client";
import type { Comment, Task } from "../types";
import StatusBadge from "./StatusBadge";

function formatDate(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function TaskCard({ task }: { task: Task }) {
  const navigate = useNavigate();
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [draft, setDraft] = useState("");
  const [count, setCount] = useState(task.comment_count);
  const [error, setError] = useState("");

  const isOverdue =
    new Date(task.deadline + "T00:00:00") < new Date(new Date().toDateString()) &&
    task.status !== "completed";

  async function toggleComments() {
    const next = !showComments;
    setShowComments(next);
    if (next && comments === null) {
      try {
        const res = await api.get<Comment[]>(`/api/tasks/${task.id}/comments`);
        setComments(res.data);
      } catch (err) {
        setError(apiError(err, "Could not load comments."));
      }
    }
  }

  async function submitComment(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim()) return;
    try {
      const res = await api.post<Comment>(`/api/tasks/${task.id}/comments`, {
        content: draft.trim(),
      });
      setComments((prev) => [...(prev ?? []), res.data]);
      setCount((c) => c + 1);
      setDraft("");
    } catch (err) {
      setError(apiError(err, "Could not post comment."));
    }
  }

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-slate-900">{task.title}</h3>
        <StatusBadge status={task.status} />
      </div>

      <p className="mt-1.5 whitespace-pre-line text-sm text-slate-600">
        {task.description}
      </p>

      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
        <span>
          <span className="font-medium text-slate-600">Deadline:</span>{" "}
          <span className={isOverdue ? "font-medium text-rose-600" : ""}>
            {formatDate(task.deadline)}
            {isOverdue && " (overdue)"}
          </span>
        </span>
        <span>
          <span className="font-medium text-slate-600">Assigned:</span>{" "}
          {task.assigned_user_name}
        </span>
        <span>
          <span className="font-medium text-slate-600">Created by:</span>{" "}
          {task.creator_name}
        </span>
      </div>

      <div className="mt-4 flex gap-2">
        {task.can_edit && (
          <button
            onClick={() => navigate(`/tasks/${task.id}/edit`)}
            className="btn-secondary !py-1.5 text-xs"
          >
            Edit
          </button>
        )}
        <button onClick={toggleComments} className="btn-secondary !py-1.5 text-xs">
          Comments ({count})
        </button>
      </div>

      {showComments && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          {error && <p className="mb-2 text-xs text-rose-600">{error}</p>}
          <div className="space-y-2">
            {comments === null ? (
              <p className="text-xs text-slate-400">Loading…</p>
            ) : comments.length === 0 ? (
              <p className="text-xs text-slate-400">No comments yet.</p>
            ) : (
              comments.map((c) => (
                <div key={c.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span className="font-medium text-slate-700">{c.author}</span>
                  <span className="text-slate-600">: {c.content}</span>
                </div>
              ))
            )}
          </div>

          <form onSubmit={submitComment} className="mt-3 flex gap-2">
            <input
              className="input flex-1"
              placeholder="Add a comment…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <button type="submit" className="btn-primary">
              Post
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
