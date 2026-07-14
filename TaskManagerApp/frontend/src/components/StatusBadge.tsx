import type { TaskStatus } from "../types";

const STYLES: Record<TaskStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  acknowledged: "bg-blue-100 text-blue-800",
  rejected: "bg-slate-200 text-slate-700",
  completed: "bg-emerald-100 text-emerald-800",
  failed: "bg-rose-100 text-rose-800",
};

export default function StatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[status]}`}
    >
      {status}
    </span>
  );
}
