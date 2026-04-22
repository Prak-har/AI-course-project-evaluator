import { Navigate } from "react-router-dom";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../api/client";
import LoginCard from "../components/LoginCard";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../utils/errors";

export default function LoginPage() {
  const navigate = useNavigate();
  const { saveUser, user, isReady } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (isReady && user) {
    return <Navigate to={user.role === "teacher" ? "/teacher" : "/student"} replace />;
  }

  const handleLogin = async (payload) => {
    setLoading(true);
    setError("");

    try {
      const user = await login(payload);
      saveUser(user);
      navigate(user.role === "teacher" ? "/teacher" : "/student");
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to sign in."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="grid w-full max-w-6xl gap-8 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="flex flex-col justify-center rounded-[2rem] bg-ink px-8 py-10 text-white md:px-12">
          <span className="data-pill w-fit bg-white/10 text-white">Continuous + final marks</span>
          <h1 className="mt-6 text-5xl font-extrabold tracking-tight">Evaluate projects with LLM plus retrieval evidence.</h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-slate-200">
            Upload project reports, run multi-step rubric scoring, inspect evidence-backed feedback, finalize marks
            ranking after the deadline, and export reports for the full class.
          </p>

          <div className="mt-10 grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-teal-200">Student view</p>
              <p className="mt-3 text-sm leading-7 text-slate-200">
                Upload a PDF or text submission, inspect draft feedback history, and review weak sections flagged by the
                evaluator.
              </p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-orange-200">Teacher view</p>
              <p className="mt-3 text-sm leading-7 text-slate-200">
                Monitor all submissions, trigger final evaluation, compare cumulative marks, and download PDF reports.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center">
          <LoginCard onSubmit={handleLogin} loading={loading} error={error} />
        </div>
      </div>
    </div>
  );
}
