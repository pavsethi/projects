import { useState } from "react";
import { TASK_STATUSES, type TaskFilters, type User } from "../types";

/**
 * Maps the original app's nine filter presets onto the backend query params.
 * The single "preset" dropdown drives which secondary control (user / status)
 * is shown.
 */
type Preset =
  | ""
  | "sort_created"
  | "sort_deadline"
  | "status"
  | "created_by_me"
  | "assigned_to_me"
  | "created_by_user"
  | "assigned_to_user"
  | "managed_created"
  | "managed_assigned";

interface Props {
  users: User[];
  currentUserId: number;
  onApply: (filters: TaskFilters) => void;
  onClear: () => void;
}

const PRESETS: { value: Preset; label: string }[] = [
  { value: "", label: "All tasks" },
  { value: "sort_created", label: "Sort by date created" },
  { value: "sort_deadline", label: "Sort by deadline" },
  { value: "status", label: "By status" },
  { value: "created_by_me", label: "Created by me" },
  { value: "assigned_to_me", label: "Assigned to me" },
  { value: "created_by_user", label: "Created by specific user" },
  { value: "assigned_to_user", label: "Assigned to specific user" },
  { value: "managed_created", label: "Created by a managed user" },
  { value: "managed_assigned", label: "Assigned to a managed user" },
];

export default function FilterBar({ users, currentUserId, onApply, onClear }: Props) {
  const [preset, setPreset] = useState<Preset>("");
  const [userId, setUserId] = useState("");
  const [status, setStatus] = useState("");

  const needsUser = preset === "created_by_user" || preset === "assigned_to_user";
  const needsStatus = preset === "status";

  function apply() {
    const f: TaskFilters = {};
    switch (preset) {
      case "sort_created":
        f.sort = "created";
        break;
      case "sort_deadline":
        f.sort = "deadline";
        break;
      case "status":
        if (status) f.status = status as TaskFilters["status"];
        break;
      case "created_by_me":
        f.created_by = currentUserId;
        break;
      case "assigned_to_me":
        f.assigned_to = currentUserId;
        break;
      case "created_by_user":
        if (userId) f.created_by = Number(userId);
        break;
      case "assigned_to_user":
        if (userId) f.assigned_to = Number(userId);
        break;
      case "managed_created":
        f.managed = "created";
        break;
      case "managed_assigned":
        f.managed = "assigned";
        break;
    }
    onApply(f);
  }

  function clear() {
    setPreset("");
    setUserId("");
    setStatus("");
    onClear();
  }

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
      <h2 className="mb-3 text-sm font-semibold text-slate-800">Filters</h2>
      <div className="space-y-3">
        <select className="input" value={preset} onChange={(e) => setPreset(e.target.value as Preset)}>
          {PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>

        {needsUser && (
          <select className="input" value={userId} onChange={(e) => setUserId(e.target.value)}>
            <option value="">Select a user…</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name}
              </option>
            ))}
          </select>
        )}

        {needsStatus && (
          <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Select a status…</option>
            {TASK_STATUSES.map((s) => (
              <option key={s} value={s} className="capitalize">
                {s}
              </option>
            ))}
          </select>
        )}

        <div className="flex gap-2">
          <button onClick={apply} className="btn-primary flex-1">
            Apply
          </button>
          <button onClick={clear} className="btn-secondary">
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}
