import { useEffect, useMemo, useState } from "react";

function normalizeTitle(value) {
  return (value || "").trim().toLowerCase();
}

export default function ContinuousUploadCard({ stages, projects, onUpload, loading }) {
  const [projectMode, setProjectMode] = useState("new");
  const [selectedProjectTitle, setSelectedProjectTitle] = useState("");
  const [newProjectTitle, setNewProjectTitle] = useState("");
  const [stageId, setStageId] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);

  const orderedProjects = useMemo(
    () => [...(projects || [])].sort((left, right) => new Date(right.created_at) - new Date(left.created_at)),
    [projects],
  );
  const orderedStages = useMemo(
    () => [...(stages || [])].sort((left, right) => left.stage_order - right.stage_order),
    [stages],
  );
  const projectTitle = projectMode === "existing" ? selectedProjectTitle : newProjectTitle;
  const matchedProject = useMemo(
    () => orderedProjects.find((project) => normalizeTitle(project.title) === normalizeTitle(projectTitle)),
    [orderedProjects, projectTitle],
  );
  const submittedStageIds = useMemo(
    () => new Set((matchedProject?.stage_submissions || []).map((submission) => submission.stage_id)),
    [matchedProject],
  );
  const availableStages = useMemo(() => {
    if (!orderedStages.length) {
      return [];
    }
    if (!matchedProject) {
      return orderedStages[0] ? [orderedStages[0]] : [];
    }

    const nextStage = orderedStages.find((stage) => !submittedStageIds.has(stage.id));
    return nextStage ? [nextStage] : [];
  }, [matchedProject, orderedStages, submittedStageIds]);

  useEffect(() => {
    if (!orderedProjects.length) {
      setProjectMode("new");
      setSelectedProjectTitle("");
      return;
    }

    if (projectMode === "existing" && !selectedProjectTitle) {
      setSelectedProjectTitle(orderedProjects[0].title);
    }
  }, [orderedProjects, projectMode, selectedProjectTitle]);

  useEffect(() => {
    if (!availableStages.find((stage) => String(stage.id) === String(stageId))) {
      setStageId(availableStages[0] ? String(availableStages[0].id) : "");
    }
  }, [availableStages, stageId]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onUpload({ projectTitle, stageId, text, file });
    if (projectTitle.trim()) {
      setProjectMode("existing");
      setSelectedProjectTitle(projectTitle.trim());
    }
    setNewProjectTitle("");
    setStageId("");
    setText("");
    setFile(null);
    event.target.reset();
  };

  return (
    <div className="section-shell">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Continuous Evaluation</h2>
        <p className="mt-2 text-sm text-slate-600">
          Submit exactly one checkpoint per stage. The portal only unlocks the next stage in chronological order for each project.
        </p>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Project</label>
          {orderedProjects.length ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 rounded-3xl bg-slate-100 p-2">
                <button
                  type="button"
                  onClick={() => setProjectMode("existing")}
                  className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${projectMode === "existing" ? "bg-white text-accent shadow-sm" : "text-slate-500"}`}
                >
                  Existing project
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setProjectMode("new");
                    setSelectedProjectTitle("");
                  }}
                  className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${projectMode === "new" ? "bg-white text-accent shadow-sm" : "text-slate-500"}`}
                >
                  New project
                </button>
              </div>

              {projectMode === "existing" ? (
                <select
                  className="input-shell"
                  value={selectedProjectTitle}
                  onChange={(event) => setSelectedProjectTitle(event.target.value)}
                  required
                >
                  <option value="">Select an existing project</option>
                  {orderedProjects.map((project) => (
                    <option key={project.id} value={project.title}>
                      {project.title}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="input-shell"
                  value={newProjectTitle}
                  onChange={(event) => setNewProjectTitle(event.target.value)}
                  placeholder="Smart Campus Monitoring System"
                  required
                />
              )}
            </div>
          ) : (
            <input
              className="input-shell"
              value={newProjectTitle}
              onChange={(event) => setNewProjectTitle(event.target.value)}
              placeholder="Smart Campus Monitoring System"
              required
            />
          )}
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Stage</label>
          <select
            className="input-shell"
            value={stageId}
            onChange={(event) => setStageId(event.target.value)}
            required
          >
            <option value="">{matchedProject ? "Only the next stage is available" : "New projects start at Stage 1"}</option>
            {availableStages.map((stage) => (
              <option key={stage.id} value={stage.id}>
                {stage.name} - max {stage.max_marks}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs text-slate-500">
            {matchedProject
              ? availableStages.length
                ? `Chronology enforced: ${availableStages[0].name} is the next stage available for ${matchedProject.title}.`
                : "All configured stages are already submitted for this project."
              : "This title will create a new project track, so only Stage 1 can be submitted first."}
          </p>
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Paste current progress</label>
          <textarea
            className="input-shell min-h-36 resize-y"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Describe what was built in this stage, what changed since the last review, and any evidence or results."
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Attach stage file</label>
          <input
            type="file"
            accept=".pdf,.txt,.md,.text"
            className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-2xl file:border-0 file:bg-accent file:px-4 file:py-3 file:font-semibold file:text-white hover:file:bg-teal-700"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </div>

        <button type="submit" className="action-button" disabled={loading || !projectTitle.trim() || !stageId || (!text.trim() && !file)}>
          {loading ? "Submitting stage..." : "Submit stage progress"}
        </button>
      </form>
    </div>
  );
}
