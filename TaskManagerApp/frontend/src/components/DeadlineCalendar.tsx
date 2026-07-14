import { useMemo, useState } from "react";
import type { Task } from "../types";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

/** Highlights the days of the visible month that have a task deadline. */
export default function DeadlineCalendar({ tasks }: { tasks: Task[] }) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());

  // Deadlines are "YYYY-MM-DD" strings; compare on that key to avoid timezone
  // shifts from parsing into a Date.
  const deadlineDays = useMemo(() => {
    const set = new Set<string>();
    for (const t of tasks) set.add(t.deadline);
    return set;
  }, [tasks]);

  const cells = useMemo(() => {
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const out: (number | null)[] = Array(firstDay).fill(null);
    for (let d = 1; d <= daysInMonth; d++) out.push(d);
    return out;
  }, [year, month]);

  const key = (day: number) =>
    `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

  function move(delta: number) {
    const next = new Date(year, month + delta, 1);
    setYear(next.getFullYear());
    setMonth(next.getMonth());
  }

  const isToday = (day: number) =>
    year === now.getFullYear() && month === now.getMonth() && day === now.getDate();

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
      <div className="mb-3 flex items-center justify-between">
        <button onClick={() => move(-1)} className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100" aria-label="Previous month">
          ‹
        </button>
        <span className="text-sm font-semibold text-slate-800">
          {MONTHS[month]} {year}
        </span>
        <button onClick={() => move(1)} className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100" aria-label="Next month">
          ›
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-xs">
        {WEEKDAYS.map((w) => (
          <div key={w} className="py-1 font-medium text-slate-400">
            {w}
          </div>
        ))}
        {cells.map((day, i) => {
          if (day === null) return <div key={`e${i}`} />;
          const hasTask = deadlineDays.has(key(day));
          return (
            <div
              key={day}
              className={[
                "grid aspect-square place-items-center rounded-md",
                hasTask ? "bg-indigo-600 font-semibold text-white" : "text-slate-600",
                !hasTask && isToday(day) ? "ring-1 ring-inset ring-indigo-400" : "",
              ].join(" ")}
              title={hasTask ? "Task deadline" : undefined}
            >
              {day}
            </div>
          );
        })}
      </div>
      <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
        <span className="inline-block h-3 w-3 rounded bg-indigo-600" /> Deadline
      </p>
    </div>
  );
}
