import { toDisplayText } from "../utils/errors";

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

function renderList(items) {
  if (!items?.length) {
    return ["Insufficient data"];
  }
  return items.map((item) => toDisplayText(item));
}

export default function FeedbackTimeline({ submissions }) {
  if (!submissions?.length) {
    return (
      <div className="section-shell">
        <h2 className="text-2xl font-bold text-ink">Feedback History</h2>
        <p className="mt-3 text-sm text-slate-600">No submissions yet. Upload a project to generate draft feedback.</p>
      </div>
    );
  }

  return (
    <div className="section-shell">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Feedback History</h2>
        <p className="mt-2 text-sm text-slate-600">Every submission and evaluation snapshot stays visible here.</p>
      </div>

      <div className="space-y-6">
        {submissions.map((submission) => (
          <div key={submission.id} className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-ink">{submission.title}</h3>
                <p className="mt-1 text-sm text-slate-500">
                  {toDisplayText(submission.original_filename, "Text submission")} - {formatDate(submission.created_at)}
                </p>
              </div>
              <span className="data-pill">{toDisplayText(submission.file_type, "text")}</span>
            </div>

            <p className="mt-4 rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-600">
              {toDisplayText(submission.content_preview)}
            </p>

            <div className="mt-5 space-y-4">
              {submission.evaluations?.length ? (
                submission.evaluations.map((evaluation) => (
                  <div key={evaluation.id} className="rounded-3xl bg-white p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-accent">{evaluation.draft ? "Draft" : "Final"} evaluation</p>
                        <p className="text-xs text-slate-500">{formatDate(evaluation.created_at)}</p>
                      </div>
                      <div className="rounded-2xl bg-accent/10 px-4 py-2 text-sm font-bold text-accent">
                        Total: {toDisplayText(evaluation.total_score)}/10
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <div>
                        <p className="mb-2 text-sm font-semibold text-slate-700">Strengths</p>
                        <ul className="space-y-2 text-sm text-slate-600">
                          {renderList(evaluation.feedback?.strengths).map((item) => (
                            <li key={item} className="rounded-2xl bg-slate-50 px-3 py-2">
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <p className="mb-2 text-sm font-semibold text-slate-700">Suggestions</p>
                        <ul className="space-y-2 text-sm text-slate-600">
                          {renderList(evaluation.feedback?.suggestions).map((item) => (
                            <li key={item} className="rounded-2xl bg-slate-50 px-3 py-2">
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="mt-4">
                      <p className="mb-2 text-sm font-semibold text-slate-700">Weak Sections</p>
                      <div className="space-y-3">
                        {evaluation.weak_sections?.length ? (
                          evaluation.weak_sections.map((item, index) => (
                            <div key={`${item.criterion}-${index}`} className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                              <p className="text-sm font-semibold text-amber-800">{toDisplayText(item.criterion, "general")}</p>
                              <p className="mt-1 text-sm text-amber-700">{toDisplayText(item.reason)}</p>
                              <p className="mt-2 text-xs leading-5 text-amber-900">{toDisplayText(item.excerpt)}</p>
                            </div>
                          ))
                        ) : (
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
                            No weak sections highlighted.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl bg-white px-4 py-3 text-sm text-slate-500">Evaluation pending.</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
