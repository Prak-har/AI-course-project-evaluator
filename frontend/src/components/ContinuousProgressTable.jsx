export default function ContinuousProgressTable({ rows, feedbackBasePath = "" }) {
  return (
    <div className="section-shell overflow-x-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Continuous Progress Review</h2>
        <p className="mt-2 text-sm text-slate-600">Track the latest checkpoint submitted for each project stage across the class.</p>
      </div>

      <table className="min-w-full overflow-hidden rounded-3xl">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.2em] text-slate-500">
            <th className="px-4 py-4">Student</th>
            <th className="px-4 py-4">Project</th>
            <th className="px-4 py-4">Stage</th>
            <th className="px-4 py-4">Scaled Score</th>
            <th className="px-4 py-4">Feedback</th>
            <th className="px-4 py-4">Follow-Through</th>
            <th className="px-4 py-4">Updated</th>
          </tr>
        </thead>
        <tbody>
          {(rows || []).map((row) => (
            <tr key={`${row.project_id}-${row.stage.stage_order}-${row.stage_submission_id}`} className="border-b border-slate-100 text-sm text-slate-700">
              <td className="px-4 py-4">
                <div className="font-semibold text-ink">{row.student.name}</div>
                <div className="text-xs text-slate-500">{row.student.email}</div>
              </td>
              <td className="px-4 py-4">
                <div className="font-semibold text-ink">{row.project_title}</div>
              </td>
              <td className="px-4 py-4">
                {row.stage.name} - max {row.stage.max_marks}
              </td>
              <td className="px-4 py-4">{typeof row.latest_score === "number" ? row.latest_score.toFixed(2) : "Pending"}</td>
              <td className="px-4 py-4">
                {feedbackBasePath ? (
                  <a
                    href={`${feedbackBasePath}/${row.stage_submission_id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="muted-button px-3 py-2 text-xs"
                  >
                    Open feedback
                  </a>
                ) : (
                  <span className="text-slate-400">Pending</span>
                )}
              </td>
              <td className="px-4 py-4 text-xs text-slate-500">
                {row.feedback?.carry_forward?.summary || "No earlier-stage follow-through signal yet."}
              </td>
              <td className="px-4 py-4">{row.created_at ? new Date(row.created_at).toLocaleString() : "Unknown"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
