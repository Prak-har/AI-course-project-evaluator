import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getStageFeedback } from "../api/client";
import Layout from "../components/Layout";
import StageMarksBreakdown from "../components/StageMarksBreakdown";
import StatCard from "../components/StatCard";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage, toDisplayText } from "../utils/errors";

function renderItems(items, fallback) {
  if (!items?.length) {
    return [fallback];
  }
  return items.map((item) => toDisplayText(item, fallback));
}

function formatMarks(earned, possible) {
  if (typeof earned !== "number") {
    return "Pending";
  }
  if (typeof possible === "number") {
    return `${earned.toFixed(2)}/${possible.toFixed(2)}`;
  }
  return earned.toFixed(2);
}

function RubricScores({ evaluation }) {
  const weights = evaluation?.rubric_weights || [];
  const scores = evaluation?.rubric_scores || {};

  if (!weights.length) {
    return null;
  }

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {weights.map((rubric) => (
        <div key={rubric.key} className="rounded-3xl border border-slate-200 bg-slate-50/70 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{rubric.later_stage_only ? "Stage 2+ Criterion" : "Rubric"}</p>
          <p className="mt-2 text-lg font-bold text-ink">{rubric.name}</p>
          <p className="mt-3 text-2xl font-extrabold text-accent">{typeof scores[rubric.key] === "number" ? scores[rubric.key].toFixed(2) : "Pending"}</p>
          <p className="mt-1 text-xs text-slate-500">
            Weight {Number(rubric.weight || 0).toFixed(2)} | Normalized {(Number(rubric.normalized_weight || 0) * 100).toFixed(1)}%
          </p>
        </div>
      ))}
    </section>
  );
}

function FeedbackList({ title, items, tone }) {
  const tones = {
    strong: "border-emerald-100 bg-emerald-50 text-emerald-900",
    risk: "border-rose-100 bg-rose-50 text-rose-900",
    action: "border-amber-100 bg-amber-50 text-amber-900",
    scope: "border-sky-100 bg-sky-50 text-sky-900",
  };

  return (
    <div className={`rounded-3xl border p-5 ${tones[tone]}`}>
      <p className="text-sm font-semibold uppercase tracking-[0.18em]">{title}</p>
      <div className="mt-3 space-y-2 text-sm leading-6">
        {renderItems(items, "Insufficient data").map((item) => (
          <p key={`${title}-${item}`} className="rounded-2xl bg-white/75 px-3 py-2">
            {item}
          </p>
        ))}
      </div>
    </div>
  );
}

export default function StageFeedbackPage() {
  const { stageSubmissionId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const response = await getStageFeedback(stageSubmissionId);
        setPayload(response);
        setError("");
      } catch (requestError) {
        setError(getErrorMessage(requestError, "Unable to load stage feedback."));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [stageSubmissionId]);

  const stageSubmission = payload?.stage_submission || null;
  const latestEvaluation = payload?.latest_evaluation || null;
  const carryForward = latestEvaluation?.feedback?.carry_forward || null;
  const backPath = user?.role === "teacher" ? "/teacher" : "/student";

  return (
    <Layout
      title={stageSubmission?.stage?.name ? `${stageSubmission.stage.name} Feedback` : "Stage Feedback"}
      subtitle="Read the full stage review in a dedicated view, including the current marks, verified recommendation follow-through, and the running stage-wise total."
      actions={
        <button type="button" className="muted-button" onClick={() => navigate(backPath)}>
          Back to dashboard
        </button>
      }
    >
      {error ? <div className="rounded-3xl bg-rose-50 px-5 py-4 text-sm text-rose-600">{error}</div> : null}

      {loading ? (
        <div className="section-shell text-sm text-slate-500">Loading stage feedback...</div>
      ) : !payload?.stage_submission ? (
        <div className="section-shell text-sm text-slate-500">Stage feedback is not available.</div>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Stage Marks"
              value={formatMarks(latestEvaluation?.scaled_score, latestEvaluation?.max_marks)}
              hint="Marks awarded for this stage alone."
            />
            <StatCard
              label="Final Marks"
              value={formatMarks(payload?.final_marks?.earned, payload?.final_marks?.possible)}
              hint="Running total built from the latest evaluated stage submissions."
            />
            <StatCard
              label="Class Rank"
              value={payload?.final_marks?.rank ? `#${payload.final_marks.rank}` : "Pending"}
              hint="Appears after the teacher finalizes marks ranking."
            />
            <StatCard
              label="Project"
              value={payload?.project?.title || "Untitled"}
              hint={payload?.student ? `${payload.student.name} • ${payload.student.email}` : "Current project track"}
            />
          </section>

          <StageMarksBreakdown
            title="Stage-wise Marks"
            subtitle="This stage contributes to the cumulative marks shown here."
            stages={payload?.stage_definitions || []}
            breakdown={payload?.stage_breakdown || []}
            finalMarks={payload?.final_marks || null}
            feedbackBasePath={`/${user?.role === "teacher" ? "teacher" : "student"}/stage-feedback`}
          />

          <RubricScores evaluation={latestEvaluation} />

          <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="section-shell">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-ink">Submission Snapshot</h2>
                <p className="mt-2 text-sm text-slate-600">
                  {stageSubmission.original_filename || "Text submission"} • {stageSubmission.created_at ? new Date(stageSubmission.created_at).toLocaleString() : "Unknown time"}
                </p>
              </div>
              <div className="rounded-3xl bg-slate-50 px-5 py-4 text-sm leading-7 text-slate-700">
                {toDisplayText(stageSubmission.content, "Insufficient data")}
              </div>
            </div>

            <div className="section-shell">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-ink">Recommendation Follow-Through</h2>
                <p className="mt-2 text-sm text-slate-600">
                  This check verifies whether earlier recommended next actions were actually carried into the current stage.
                </p>
              </div>

              <div className="rounded-3xl bg-slate-50 px-5 py-4 text-sm leading-7 text-slate-700">
                {toDisplayText(carryForward?.summary, "No previous-stage recommendations to compare yet.")}
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <FeedbackList title="Addressed Earlier" items={carryForward?.addressed_items} tone="strong" />
                <FeedbackList title="Still Pending" items={carryForward?.pending_items} tone="action" />
              </div>
            </div>
          </section>

          <section className="grid gap-4 xl:grid-cols-2">
            <FeedbackList title="Strong Areas" items={latestEvaluation?.feedback?.strengths} tone="strong" />
            <FeedbackList title="Needs Work" items={latestEvaluation?.feedback?.weaknesses} tone="risk" />
            <FeedbackList title="Recommended Next Actions" items={latestEvaluation?.feedback?.suggestions} tone="action" />
            <FeedbackList title="Future Scope" items={latestEvaluation?.feedback?.future_scope} tone="scope" />
          </section>

          <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="section-shell">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-ink">Weak Sections</h2>
                <p className="mt-2 text-sm text-slate-600">Text regions that contributed to lower marks in this stage.</p>
              </div>

              <div className="space-y-4">
                {(latestEvaluation?.weak_sections || []).length ? (
                  latestEvaluation.weak_sections.map((item, index) => (
                    <div key={`${item.criterion}-${index}`} className="rounded-3xl border border-rose-100 bg-rose-50 p-4">
                      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-rose-700">{toDisplayText(item.criterion, "General")}</p>
                      <p className="mt-2 text-sm leading-6 text-rose-900">{toDisplayText(item.reason, "Insufficient data")}</p>
                      <p className="mt-3 rounded-2xl bg-white/75 px-4 py-3 text-sm leading-6 text-slate-700">{toDisplayText(item.excerpt, "Insufficient data")}</p>
                    </div>
                  ))
                ) : (
                  <div className="rounded-3xl border border-dashed border-slate-300 px-5 py-8 text-sm text-slate-500">
                    No weak-section evidence was stored for this stage.
                  </div>
                )}
              </div>
            </div>

            <div className="section-shell">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-ink">Retrieved Evidence</h2>
                <p className="mt-2 text-sm text-slate-600">Top evidence chunks that were used while evaluating this stage.</p>
              </div>

              <div className="space-y-4">
                {(latestEvaluation?.retrieved_chunks || []).length ? (
                  latestEvaluation.retrieved_chunks.map((chunk) => (
                    <div key={chunk.chunk_id} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-ink">Chunk #{chunk.chunk_id}</p>
                        <span className="data-pill">Score {toDisplayText(chunk.score, "N/A")}</span>
                      </div>
                      <p className="mt-3 rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-700">
                        {toDisplayText(chunk.text, "Insufficient data")}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="rounded-3xl border border-dashed border-slate-300 px-5 py-8 text-sm text-slate-500">
                    Retrieved evidence is not available for this stage yet.
                  </div>
                )}
              </div>
            </div>
          </section>
        </>
      )}
    </Layout>
  );
}
