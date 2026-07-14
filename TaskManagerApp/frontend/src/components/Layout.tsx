import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="bg-slate-900 text-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2 text-lg font-semibold">
            <span className="grid h-7 w-7 place-items-center rounded-md bg-indigo-500 text-sm">
              ✓
            </span>
            Task Manager
          </Link>
          <div className="flex items-center gap-4 text-sm">
            {user && (
              <span className="hidden text-slate-300 sm:inline">
                {user.full_name}
              </span>
            )}
            <button
              onClick={logout}
              className="rounded-md border border-slate-600 px-3 py-1.5 text-slate-200 transition hover:bg-slate-800"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
