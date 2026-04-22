import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function Layout({ title, subtitle, actions, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen px-4 py-6 md:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="glass-card overflow-hidden">
          <div className="flex flex-col gap-6 border-b border-slate-100 p-6 md:flex-row md:items-center md:justify-between md:p-8">
            <div className="space-y-3">
              <span className="data-pill bg-accent/10 text-accent">AI Course Project Evaluator</span>
              <div>
                <h1 className="text-3xl font-extrabold tracking-tight text-ink">{title}</h1>
                <p className="mt-2 max-w-2xl text-sm text-slate-600">{subtitle}</p>
              </div>
            </div>

            <div className="flex flex-col items-start gap-3 md:items-end">
              <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <div className="font-semibold">{user?.name}</div>
                <div className="text-slate-500">{user?.email}</div>
                <div className="mt-1 uppercase tracking-[0.2em] text-xs text-accent">{user?.role}</div>
              </div>
              <button type="button" className="muted-button" onClick={handleLogout}>
                Sign out
              </button>
            </div>
          </div>

          {actions ? <div className="flex flex-wrap gap-3 p-6 md:p-8">{actions}</div> : null}
        </header>

        {children}
      </div>
    </div>
  );
}

