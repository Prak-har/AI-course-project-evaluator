import { toDisplayText } from "../utils/errors";

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

function getLatestEvaluation(stageSubmission) {
  if (!stageSubmission?.evaluations?.length) {
    return null;
  }
  return [...stageSubmission.evaluations].sort((left, right) => new Date(right.created_at) - new Date(left.created_at))[0];
}

function renderItems(items, fallback) {
  if (!items?.length) {
    return [fallback];
  }
  return items.map((item) => toDisplayText(item, fallback));
}

export default function ContinuousProgressTimeline({ projects, onDelete, deletingStageId, feedbackBasePath = "" }) {
  if (!projects?.length) {
    return (
      <div className="section-shell">
        <h2 className="text-2xl font-bold text-ink">Stage Progress</h2>
        <p className="mt-3 text-sm text-slate-600">No stage submissions yet. Submit the first progress checkpoint to start continuous evaluation.</p>
      </div>
    );
  }

  return (
    <div className="section-shell">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Stage Progress</h2>
        <p className="mt-2 text-sm text-slate-600">Every project checkpoint stays visible with its scaled stage score and feedback context.</p>
      </div>

      <div className="space-y-6">
        {projects.map((project) => (
          <div key={project.id} className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-ink">{project.title}</h3>
                <p className="mt-1 text-xs text-slate-500">Created {formatDate(project.created_at)}</p>
              </div>
              <span className="data-pill">{project.stage_submissions?.length || 0} stage uploads</span>
            </div>

            <div className="mt-5 space-y-4">
              {[...(project.stage_submissions || [])]
                .sort((left, right) => {
                  const orderDiff = (left.stage?.stage_order || 0) - (right.stage?.stage_order || 0);
                  if (orderDiff !== 0) {
                    return orderDiff;
                  }
                  return new Date(right.created_at) - new Date(left.created_at);
                })
                .map((stageSubmission) => {
                  const latestEvaluation = getLatestEvaluation(stageSubmission);
                  const carryForward = latestEvaluation?.feedback?.carry_forward;
                  return (
                    <div key={stageSubmission.id} className="rounded-3xl bg-white p-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-accent">
                            {stageSubmission.stage?.name || "Stage"} - max {toDisplayText(stageSubmission.stage?.max_marks, "N/A")}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            {toDisplayText(stageSubmission.original_filename, "Text submission")} - {formatDate(stageSubmission.created_at)}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="rounded-2xl bg-accent/10 px-4 py-2 text-sm font-bold text-accent">
                            {latestEvaluation ? `${latestEvaluation.scaled_score}/${latestEvaluation.max_marks}` : "Pending"}
                          </div>
                          {feedbackBasePath ? (
                            <a
                              href={`${feedbackBasePath}/${stageSubmission.id}`}
                              target="_blank"
                              rel="noreferrer"
                              className="muted-button px-3 py-2 text-xs"
                            >
                              Open feedback
                            </a>
                          ) : null}
                          {onDelete ? (
                            <button
                              type="button"
                              className="inline-flex items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 transition hover:border-rose-300 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={deletingStageId === stageSubmission.id}
                              onClick={() => onDelete(stageSubmission)}
                            >
                              {deletingStageId === stageSubmission.id ? "Deleting..." : "Delete"}
                            </button>
                          ) : null}
                        </div>
                      </div>

                      <p className="mt-4 rounded-2xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
                        {toDisplayText(stageSubmission.content_preview)}
                      </p>

                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3">
                          <p className="text-sm font-semibold text-emerald-900">Strong Areas</p>
                          <div className="mt-2 space-y-2 text-sm text-emerald-800">
                            {renderItems(latestEvaluation?.feedback?.strengths, "Insufficient data").map((item) => (
                              <p key={`${stageSubmission.id}-strength-${item}`} className="rounded-2xl bg-white/70 px-3 py-2">
                                {item}
                              </p>
                            ))}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3">
                          <p className="text-sm font-semibold text-rose-900">Needs Work</p>
                          <div className="mt-2 space-y-2 text-sm text-rose-800">
                            {renderItems(latestEvaluation?.feedback?.weaknesses, "Insufficient data").map((item) => (
                              <p key={`${stageSubmission.id}-weak-${item}`} className="rounded-2xl bg-white/70 px-3 py-2">
                                {item}
                              </p>
                            ))}
                          </div>
                        </div>
                      </div>

                      {carryForward ? (
                        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                          <p className="text-sm font-semibold text-ink">Recommendation Follow-Through</p>
                          <p className="mt-2 text-sm leading-6 text-slate-600">
                            {toDisplayText(carryForward.summary, "Insufficient data")}
                          </p>

                          <div className="mt-3 grid gap-3 md:grid-cols-2">
                            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3">
                              <p className="text-sm font-semibold text-emerald-900">Addressed Earlier</p>
                              <div className="mt-2 space-y-2 text-sm text-emerald-800">
                                {renderItems(carryForward.addressed_items, "No completed follow-through called out yet.").map((item) => (
                                  <p key={`${stageSubmission.id}-carry-addressed-${item}`} className="rounded-2xl bg-white/70 px-3 py-2">
                                    {item}
                                  </p>
                                ))}
                              </div>
                            </div>

                            <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                              <p className="text-sm font-semibold text-amber-900">Still Pending</p>
                              <div className="mt-2 space-y-2 text-sm text-amber-800">
                                {renderItems(carryForward.pending_items, "No pending carry-forward items were flagged.").map((item) => (
                                  <p key={`${stageSubmission.id}-carry-pending-${item}`} className="rounded-2xl bg-white/70 px-3 py-2">
                                    {item}
                                  </p>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
