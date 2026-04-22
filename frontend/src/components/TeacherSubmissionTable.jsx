export default function TeacherSubmissionTable({ rows, onEvaluate, onDelete, processing, busyStudentId, busyAction }) {
  const formatMarks = (earned, possible) => {
    if (typeof earned !== "number") {
      return "Pending";
    }
    if (typeof possible === "number") {
      return `${earned.toFixed(2)}/${possible.toFixed(2)}`;
    }
    return earned.toFixed(2);
  };

  const formatSigned = (value) => {
    if (typeof value !== "number") {
      return "N/A";
    }
    return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
  };

  return (
    <div className="section-shell overflow-x-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Submission Review</h2>
        <p className="mt-2 text-sm text-slate-600">
          Review current submissions, trigger evaluation, inspect cumulative marks, and download reports.
        </p>
      </div>

      <table className="min-w-full overflow-hidden rounded-3xl">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.2em] text-slate-500">
            <th className="px-4 py-4">Student</th>
            <th className="px-4 py-4">Submission</th>
            <th className="px-4 py-4">Draft</th>
            <th className="px-4 py-4">Final Marks</th>
            <th className="px-4 py-4">Comparison</th>
            <th className="px-4 py-4">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const activeSubmission = row.latest_stage_submission || row.latest_submission;
            const draftScore = row.latest_stage_evaluation?.scaled_score ?? row.latest_draft?.total_score;
            const draftOutOf = row.latest_stage_evaluation?.max_marks ?? (row.latest_draft ? 10 : null);
            const finalScore = row.final_marks?.earned ?? null;
            const finalOutOf = row.final_marks?.possible ?? null;
            const isStageBased = Boolean(row.latest_stage_submission);

            return (
              <tr key={row.student.id} className="border-b border-slate-100 text-sm text-slate-700">
                <td className="px-4 py-4">
                  <div className="font-semibold text-ink">{row.student.name}</div>
                  <div className="text-xs text-slate-500">{row.student.email}</div>
                </td>
                <td className="px-4 py-4">
                  {activeSubmission ? (
                    <>
                      <div className="font-semibold text-ink">{activeSubmission.title}</div>
                      <div className="text-xs text-slate-500">
                        {activeSubmission.stage?.name
                          ? `${activeSubmission.stage.name} - ${activeSubmission.original_filename || "Text submission"}`
                          : activeSubmission.original_filename || "Text submission"}
                      </div>
                    </>
                  ) : (
                    <span className="text-slate-400">No submission</span>
                  )}
                </td>
                <td className="px-4 py-4">{typeof draftScore === "number" ? formatMarks(draftScore, draftOutOf) : "Pending"}</td>
                <td className="px-4 py-4">{formatMarks(finalScore, finalOutOf)}</td>
                <td className="px-4 py-4">
                  {row.comparison ? (
                    <div className="space-y-1 rounded-2xl bg-accent/10 px-3 py-3 text-xs text-accent">
                      <div className="font-semibold text-ink">
                        {row.final_marks?.rank ? `Rank #${row.final_marks.rank}/${row.comparison.ranked_count}` : "Awaiting final rank"}
                      </div>
                      <div>Avg {formatMarks(row.comparison.class_average, row.comparison.total_possible_marks)}</div>
                      <div>Top {formatMarks(row.comparison.top_score, row.comparison.total_possible_marks)}</div>
                      <div>Delta {formatSigned(row.comparison.difference_from_average)}</div>
                    </div>
                  ) : (
                    <span className="text-slate-400">Pending</span>
                  )}
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="muted-button px-3 py-2 text-xs"
                      disabled={processing || !activeSubmission}
                      onClick={() => onEvaluate({ kind: isStageBased ? "stage" : "submission", row })}
                    >
                      {busyAction === "evaluate" && busyStudentId === row.student.id ? "Evaluating..." : "Review evaluate"}
                    </button>
                    {row.latest_submission ? (
                      <a
                        href={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/teacher/report/${row.latest_submission.id}`}
                        className="muted-button px-3 py-2 text-xs"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Report PDF
                      </a>
                    ) : null}
                    {row.latest_stage_submission ? (
                      <a
                        href={`/teacher/stage-feedback/${row.latest_stage_submission.id}`}
                        className="muted-button px-3 py-2 text-xs"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Stage feedback
                      </a>
                    ) : null}
                    <button
                      type="button"
                      className="inline-flex items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 transition hover:border-rose-300 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={processing}
                      onClick={() => onDelete(row.student)}
                    >
                      {busyAction === "delete" && busyStudentId === row.student.id ? "Deleting..." : "Delete student"}
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
