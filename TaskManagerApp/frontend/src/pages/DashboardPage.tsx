import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Task, TaskFilters, User } from "../types";
import FilterBar from "../components/FilterBar";
import DeadlineCalendar from "../components/DeadlineCalendar";
import TaskCard from "../components/TaskCard";

export default function DashboardPage() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTasks = useCallback(async (filters: TaskFilters = {}) => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<Task[]>("/api/tasks", { params: filters });
      setTasks(res.data);
    } catch (err) {
      setError(apiError(err, "Could not load tasks."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    api.get<User[]>("/api/users").then((res) => setUsers(res.data)).catch(() => {});
  }, [loadTasks]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Tasks</h1>
          <p className="text-sm text-slate-500">
            Tasks you created, are assigned, or that your reports created.
          </p>
        </div>
        <Link to="/tasks/new" className="btn-primary">
          + New task
        </Link>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div className="space-y-4">
          {loading ? (
            <p className="text-sm text-slate-400">Loading tasks…</p>
          ) : error ? (
            <p className="text-sm text-rose-600">{error}</p>
          ) : tasks.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
              <p className="text-slate-500">No tasks match.</p>
              <Link to="/tasks/new" className="mt-3 inline-block text-sm font-medium text-indigo-600 hover:underline">
                Create your first task
              </Link>
            </div>
          ) : (
            tasks.map((task) => <TaskCard key={task.id} task={task} />)
          )}
        </div>

        <aside className="space-y-6">
          {user && (
            <FilterBar
              users={users}
              currentUserId={user.id}
              onApply={loadTasks}
              onClear={() => loadTasks()}
            />
          )}
          <DeadlineCalendar tasks={tasks} />
        </aside>
      </div>
    </div>
  );
}
