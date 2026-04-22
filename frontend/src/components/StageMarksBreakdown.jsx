function formatMarks(earned, possible) {
  if (typeof earned !== "number") {
    return "Pending";
  }
  if (typeof possible === "number") {
    return `${earned.toFixed(2)}/${possible.toFixed(2)}`;
  }
  return earned.toFixed(2);
}

export default function StageMarksBreakdown({ title = "Stage-wise Marks", subtitle, stages, breakdown, finalMarks, feedbackBasePath = "" }) {
  const orderedStages = [...(stages || [])].sort((left, right) => left.stage_order - right.stage_order);
  const breakdownByStage = new Map((breakdown || []).map((item) => [item.stage_id || item.stage_order, item]));

  return (
    <div className="section-shell">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-ink">{title}</h2>
          <p className="mt-2 text-sm text-slate-600">
            {subtitle || "See how the final marks are built from the latest evaluated submission in each stage."}
          </p>
        </div>
        <div className="rounded-3xl bg-accent/10 px-5 py-4 text-right">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Total</p>
          <p className="mt-2 text-2xl font-extrabold text-ink">{formatMarks(finalMarks?.earned, finalMarks?.possible)}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {orderedStages.map((stage) => {
          const stageMarks = breakdownByStage.get(stage.id) || breakdownByStage.get(stage.stage_order);
          return (
            <div key={stage.id} className="rounded-3xl border border-slate-200 bg-slate-50/80 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">{stage.name}</p>
                  <p className="mt-2 text-xl font-extrabold text-ink">
                    {formatMarks(stageMarks?.scaled_score, stage.max_marks)}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className="data-pill">Stage {stage.stage_order}</span>
                  {feedbackBasePath && stageMarks?.submission_id ? (
                    <a
                      href={`${feedbackBasePath}/${stageMarks.submission_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="muted-button px-3 py-2 text-xs"
                    >
                      Open feedback
                    </a>
                  ) : null}
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-500">
                {typeof stageMarks?.raw_total_score === "number"
                  ? `Rubric score ${stageMarks.raw_total_score.toFixed(2)}/10`
                  : "Not evaluated yet."}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
