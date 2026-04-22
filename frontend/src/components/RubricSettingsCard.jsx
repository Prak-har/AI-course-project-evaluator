import { useEffect, useMemo, useState } from "react";

export default function RubricSettingsCard({
  rubrics,
  onSave,
  onCreate,
  onDelete,
  savingRubricId,
  deletingRubricId,
  creatingRubric,
}) {
  const [drafts, setDrafts] = useState({});
  const [newRubric, setNewRubric] = useState({
    name: "",
    weight: "",
    later_stage_only: false,
  });

  useEffect(() => {
    const nextDrafts = {};
    for (const rubric of rubrics || []) {
      nextDrafts[rubric.id] = {
        name: rubric.name,
        weight: rubric.weight,
        later_stage_only: rubric.later_stage_only,
      };
    }
    setDrafts(nextDrafts);
  }, [rubrics]);

  const baseWeight = useMemo(
    () =>
      (rubrics || [])
        .filter((rubric) => !rubric.later_stage_only)
        .reduce((sum, rubric) => sum + Number(rubric.weight || 0), 0),
    [rubrics],
  );

  const laterStageWeight = useMemo(
    () =>
      (rubrics || [])
        .filter((rubric) => rubric.later_stage_only)
        .reduce((sum, rubric) => sum + Number(rubric.weight || 0), 0),
    [rubrics],
  );

  const updateDraft = (rubricId, field, value) => {
    setDrafts((current) => ({
      ...current,
      [rubricId]: {
        ...current[rubricId],
        [field]: value,
      },
    }));
  };

  const handleCreate = async () => {
    await onCreate(newRubric);
    setNewRubric({
      name: "",
      weight: "",
      later_stage_only: false,
    });
  };

  return (
    <div className="section-shell">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Scoring Rubrics</h2>
        <p className="mt-2 text-sm text-slate-600">
          Control the scoring criteria and their percentage-style weights from here. Later-stage-only rubrics are applied from Stage 2 onward and are normalized together with the base rubrics.
        </p>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 bg-slate-50/70 px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Base Rubric Weight Total</p>
          <p className="mt-2 text-2xl font-bold text-ink">{baseWeight.toFixed(2)}</p>
          <p className="mt-1 text-xs text-slate-500">Used for legacy evaluations and Stage 1.</p>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-slate-50/70 px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Stage 2+ Extra Weight</p>
          <p className="mt-2 text-2xl font-bold text-ink">{laterStageWeight.toFixed(2)}</p>
          <p className="mt-1 text-xs text-slate-500">Applied only when previous-stage feedback follow-through should affect the score.</p>
        </div>
      </div>

      <div className="space-y-4">
        {(rubrics || []).map((rubric) => (
          <div key={rubric.id} className="rounded-3xl border border-slate-200 bg-slate-50/70 p-4">
            <div className="grid gap-4 lg:grid-cols-[1.2fr_0.5fr_0.7fr_auto_auto] lg:items-end">
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Rubric Name</label>
                <input
                  className="input-shell"
                  value={drafts[rubric.id]?.name || ""}
                  onChange={(event) => updateDraft(rubric.id, "name", event.target.value)}
                />
              </div>

              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Weight</label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  className="input-shell"
                  value={drafts[rubric.id]?.weight ?? ""}
                  onChange={(event) => updateDraft(rubric.id, "weight", event.target.value)}
                />
              </div>

              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={Boolean(drafts[rubric.id]?.later_stage_only)}
                  onChange={(event) => updateDraft(rubric.id, "later_stage_only", event.target.checked)}
                />
                Stage 2+ only
              </label>

              <button
                type="button"
                className="action-button"
                disabled={savingRubricId === rubric.id}
                onClick={() => onSave(rubric.id, drafts[rubric.id])}
              >
                {savingRubricId === rubric.id ? "Saving..." : "Save"}
              </button>

              <button
                type="button"
                className="inline-flex items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 transition hover:border-rose-300 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={deletingRubricId === rubric.id}
                onClick={() => onDelete(rubric)}
              >
                {deletingRubricId === rubric.id ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white p-4">
        <h3 className="text-lg font-bold text-ink">Add Rubric</h3>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.5fr_0.7fr_auto] lg:items-end">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Rubric Name</label>
            <input
              className="input-shell"
              value={newRubric.name}
              onChange={(event) => setNewRubric((current) => ({ ...current, name: event.target.value }))}
              placeholder="Research Rigor"
            />
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Weight</label>
            <input
              type="number"
              min="0"
              step="0.5"
              className="input-shell"
              value={newRubric.weight}
              onChange={(event) => setNewRubric((current) => ({ ...current, weight: event.target.value }))}
              placeholder="10"
            />
          </div>

          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={newRubric.later_stage_only}
              onChange={(event) => setNewRubric((current) => ({ ...current, later_stage_only: event.target.checked }))}
            />
            Stage 2+ only
          </label>

          <button
            type="button"
            className="action-button"
            disabled={creatingRubric || !newRubric.name.trim() || newRubric.weight === ""}
            onClick={handleCreate}
          >
            {creatingRubric ? "Adding..." : "Add rubric"}
          </button>
        </div>
      </div>
    </div>
  );
}
