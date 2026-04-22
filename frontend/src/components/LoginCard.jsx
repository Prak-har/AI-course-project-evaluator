import { useState } from "react";

export default function LoginCard({ onSubmit, loading, error }) {
  const [role, setRole] = useState("student");
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
  });

  const updateField = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSubmit({
      role,
      email: form.email,
      name: role === "student" ? form.name : undefined,
      password: role === "teacher" ? form.password : undefined,
    });
  };

  return (
    <div className="glass-card w-full max-w-xl p-8 md:p-10">
      <div className="mb-8">
        <span className="data-pill bg-accent/10 text-accent">Role-aware access</span>
        <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">Sign in to your evaluation workspace</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Students can upload projects and track draft feedback. Teachers can review all submissions, run final
          evaluation, rank the class, and download reports.
        </p>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 gap-3 rounded-3xl bg-slate-100 p-2">
          {["student", "teacher"].map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setRole(option)}
              className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                role === option ? "bg-white text-accent shadow-sm" : "text-slate-500"
              }`}
            >
              {option === "student" ? "Student" : "Teacher"}
            </button>
          ))}
        </div>

        {role === "student" ? (
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">Name</label>
            <input
              className="input-shell"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              placeholder="Aarav Sharma"
            />
          </div>
        ) : null}

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Email</label>
          <input
            type="email"
            className="input-shell"
            value={form.email}
            onChange={(event) => updateField("email", event.target.value)}
            placeholder={role === "teacher" ? "teacher@example.com" : "student@example.com"}
            required
          />
        </div>

        {role === "teacher" ? (
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">Password</label>
            <input
              type="password"
              className="input-shell"
              value={form.password}
              onChange={(event) => updateField("password", event.target.value)}
              placeholder="teach123"
              required
            />
            <p className="mt-2 text-xs text-slate-500">Demo teacher credentials: teacher@example.com / teach123</p>
          </div>
        ) : null}

        {error ? <div className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-600">{error}</div> : null}

        <button type="submit" className="action-button w-full" disabled={loading}>
          {loading ? "Signing in..." : role === "teacher" ? "Enter teacher dashboard" : "Enter student dashboard"}
        </button>
      </form>
    </div>
  );
}

