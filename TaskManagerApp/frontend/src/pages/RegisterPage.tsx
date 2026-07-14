import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api, apiError } from "../api/client";
import type { User } from "../types";

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    password: "",
    manager_id: "",
  });
  const [managers, setManagers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Load existing users so a new hire can pick their manager.
  useEffect(() => {
    api
      .get<User[]>("/api/users")
      .then((res) => setManagers(res.data))
      .catch(() => setManagers([]));
  }, []);

  if (user) return <Navigate to="/" replace />;

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register({
        first_name: form.first_name,
        last_name: form.last_name,
        username: form.username,
        email: form.email,
        password: form.password,
        manager_id: form.manager_id ? Number(form.manager_id) : null,
      });
      navigate("/");
    } catch (err) {
      setError(apiError(err, "Registration failed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
        <h1 className="text-2xl font-semibold text-slate-900">Create your account</h1>

        {managers.length === 0 && (
          <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            You are the first user — leave the manager field empty. You'll act as the
            admin.
          </p>
        )}

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="First name">
              <input className="input" value={form.first_name} onChange={set("first_name")} required />
            </Field>
            <Field label="Last name">
              <input className="input" value={form.last_name} onChange={set("last_name")} required />
            </Field>
          </div>
          <Field label="Username">
            <input className="input" value={form.username} onChange={set("username")} required minLength={3} />
          </Field>
          <Field label="Email">
            <input type="email" className="input" value={form.email} onChange={set("email")} required />
          </Field>
          <Field label="Password">
            <input
              type="password"
              className="input"
              value={form.password}
              onChange={set("password")}
              required
              minLength={6}
            />
          </Field>
          <Field label="Manager (optional)">
            <select className="input" value={form.manager_id} onChange={set("manager_id")}>
              <option value="">No manager</option>
              {managers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name}
                </option>
              ))}
            </select>
          </Field>

          {error && <p className="text-sm text-rose-600">{error}</p>}

          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? "Creating…" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-indigo-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
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
