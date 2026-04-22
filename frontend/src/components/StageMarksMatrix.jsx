function formatMarks(earned, possible) {
  if (typeof earned !== "number") {
    return "Pending";
  }
  if (typeof possible === "number") {
    return `${earned.toFixed(2)}/${possible.toFixed(2)}`;
  }
  return earned.toFixed(2);
}

export default function StageMarksMatrix({ rows, stages, feedbackBasePath = "" }) {
  const orderedStages = [...(stages || [])].sort((left, right) => left.stage_order - right.stage_order);

  return (
    <div className="section-shell overflow-x-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Stage-wise Marks Distribution</h2>
        <p className="mt-2 text-sm text-slate-600">Compare how each student is performing across the individual project stages.</p>
      </div>

      <table className="min-w-full overflow-hidden rounded-3xl">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.2em] text-slate-500">
            <th className="px-4 py-4">Student</th>
            {orderedStages.map((stage) => (
              <th key={stage.id} className="px-4 py-4">
                {stage.name}
              </th>
            ))}
            <th className="px-4 py-4">Total</th>
            <th className="px-4 py-4">Rank</th>
          </tr>
        </thead>
        <tbody>
          {(rows || []).map((row) => {
            const stageMap = new Map((row.stage_breakdown || []).map((item) => [item.stage_id || item.stage_order, item]));
            return (
              <tr key={row.student.id} className="border-b border-slate-100 text-sm text-slate-700">
                <td className="px-4 py-4">
                  <div className="font-semibold text-ink">{row.student.name}</div>
                  <div className="text-xs text-slate-500">{row.student.email}</div>
                </td>
                {orderedStages.map((stage) => {
                  const stageMarks = stageMap.get(stage.id) || stageMap.get(stage.stage_order);
                  return (
                    <td key={`${row.student.id}-${stage.id}`} className="px-4 py-4">
                      {feedbackBasePath && stageMarks?.submission_id ? (
                        <a
                          href={`${feedbackBasePath}/${stageMarks.submission_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="font-semibold text-accent underline-offset-4 hover:underline"
                        >
                          {formatMarks(stageMarks?.scaled_score, stage.max_marks)}
                        </a>
                      ) : (
                        formatMarks(stageMarks?.scaled_score, stage.max_marks)
                      )}
                    </td>
                  );
                })}
                <td className="px-4 py-4 font-semibold text-ink">{formatMarks(row.final_marks?.earned, row.final_marks?.possible)}</td>
                <td className="px-4 py-4">{row.final_marks?.rank ? `#${row.final_marks.rank}` : "Pending"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
