import { useEffect, useState } from "react";

export default function StageSettingsCard({
  stages,
  onSave,
  onCreate,
  onDelete,
  savingStageId,
  deletingStageId,
  creatingStage,
}) {
  const [drafts, setDrafts] = useState({});
  const [newStage, setNewStage] = useState({
    name: "",
    max_marks: "",
  });

  useEffect(() => {
    const nextDrafts = {};
    for (const stage of stages || []) {
      nextDrafts[stage.id] = {
        name: stage.name,
        max_marks: stage.max_marks,
      };
    }
    setDrafts(nextDrafts);
  }, [stages]);

  const updateDraft = (stageId, field, value) => {
    setDrafts((current) => ({
      ...current,
      [stageId]: {
        ...current[stageId],
        [field]: value,
      },
    }));
  };

  const handleCreate = async () => {
    await onCreate(newStage);
    setNewStage({
      name: "",
      max_marks: "",
    });
  };

  return (
    <div className="section-shell">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Continuous Stage Settings</h2>
        <p className="mt-2 text-sm text-slate-600">
          Control the total number of stages and the marks allocated to each one. Adding a stage increases the total program marks, and deleting is restricted to the last unused stage so chronology stays stable.
        </p>
      </div>

      <div className="space-y-4">
        {(stages || []).map((stage) => (
          <div key={stage.id} className="rounded-3xl border border-slate-200 bg-slate-50/70 p-4">
            <div className="grid gap-4 lg:grid-cols-[1.1fr_0.5fr_0.5fr_auto_auto] lg:items-end">
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Stage Name</label>
                <input
                  className="input-shell"
                  value={drafts[stage.id]?.name || ""}
                  onChange={(event) => updateDraft(stage.id, "name", event.target.value)}
                />
              </div>

              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Stage Order</label>
                <div className="input-shell bg-slate-100 text-slate-500">{stage.stage_order}</div>
              </div>

              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Max Marks</label>
                <input
                  type="number"
                  min="1"
                  step="0.5"
                  className="input-shell"
                  value={drafts[stage.id]?.max_marks ?? ""}
                  onChange={(event) => updateDraft(stage.id, "max_marks", event.target.value)}
                />
              </div>

              <button
                type="button"
                className="action-button"
                disabled={savingStageId === stage.id}
                onClick={() => onSave(stage.id, drafts[stage.id])}
              >
                {savingStageId === stage.id ? "Saving..." : "Save"}
              </button>

              <button
                type="button"
                className="inline-flex items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 transition hover:border-rose-300 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={deletingStageId === stage.id}
                onClick={() => onDelete(stage)}
              >
                {deletingStageId === stage.id ? "Deleting..." : "Delete"}
              </button>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Submissions linked: {stage.submission_count || 0}. Only the last stage with zero submissions can be deleted.
            </p>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white p-4">
        <h3 className="text-lg font-bold text-ink">Add Stage</h3>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.5fr_auto] lg:items-end">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Stage Name</label>
            <input
              className="input-shell"
              value={newStage.name}
              onChange={(event) => setNewStage((current) => ({ ...current, name: event.target.value }))}
              placeholder="Stage 4"
            />
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Max Marks</label>
            <input
              type="number"
              min="1"
              step="0.5"
              className="input-shell"
              value={newStage.max_marks}
              onChange={(event) => setNewStage((current) => ({ ...current, max_marks: event.target.value }))}
              placeholder="10"
            />
          </div>

          <button
            type="button"
            className="action-button"
            disabled={creatingStage || !newStage.name.trim() || newStage.max_marks === ""}
            onClick={handleCreate}
          >
            {creatingStage ? "Adding..." : "Add stage"}
          </button>
        </div>
      </div>
    </div>
  );
}
