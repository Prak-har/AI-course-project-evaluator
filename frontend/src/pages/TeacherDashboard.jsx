import { useEffect, useState } from "react";

import {
  createRubric,
  createStage,
  deleteRubric,
  deleteStage,
  deleteStudent,
  evaluateStageProgress,
  evaluateSubmission,
  finalizeGrades,
  getTeacherDashboard,
  updateRubric,
  updateStage,
  uploadMasterBrief,
} from "../api/client";
import ContinuousProgressTable from "../components/ContinuousProgressTable";
import Layout from "../components/Layout";
import MasterBriefCard from "../components/MasterBriefCard";
import MarksComparisonChart from "../components/MarksComparisonChart";
import RubricSettingsCard from "../components/RubricSettingsCard";
import ScoreBreakdownChart from "../components/ScoreBreakdownChart";
import StageMarksMatrix from "../components/StageMarksMatrix";
import StageSettingsCard from "../components/StageSettingsCard";
import StatCard from "../components/StatCard";
import TeacherSubmissionTable from "../components/TeacherSubmissionTable";
import { getErrorMessage } from "../utils/errors";

function getTopEvaluation(rows) {
  const evaluations = rows
    .map((row) => row.latest_stage_evaluation || row.latest_final || row.latest_draft)
    .filter(Boolean)
    .sort((left, right) => (right.scaled_score ?? right.total_score ?? 0) - (left.scaled_score ?? left.total_score ?? 0));

  return evaluations[0] || null;
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

export default function TeacherDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [busyStudentId, setBusyStudentId] = useState(null);
  const [busyAction, setBusyAction] = useState("");
  const [savingStageId, setSavingStageId] = useState(null);
  const [deletingStageId, setDeletingStageId] = useState(null);
  const [creatingStage, setCreatingStage] = useState(false);
  const [savingRubricId, setSavingRubricId] = useState(null);
  const [deletingRubricId, setDeletingRubricId] = useState(null);
  const [creatingRubric, setCreatingRubric] = useState(false);
  const [masterBriefLoading, setMasterBriefLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const response = await getTeacherDashboard();
      setDashboard(response);
      setError("");
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to load teacher dashboard."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleFinalize = async () => {
    setProcessing(true);
    setBusyStudentId(null);
    setBusyAction("finalize");
    setError("");
    setNotice("");

    try {
      await finalizeGrades();
      setNotice("Final marks and class comparison refreshed successfully.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to finalize the marks comparison."));
    } finally {
      setProcessing(false);
      setBusyAction("");
    }
  };

  const handleFinalEvaluation = async (target) => {
    const targetRow = target?.row;
    setProcessing(true);
    setBusyStudentId(targetRow?.student?.id ?? null);
    setBusyAction("evaluate");
    setError("");
    setNotice("");

    try {
      if (target?.kind === "stage") {
        await evaluateStageProgress({ stage_submission_id: target.row.latest_stage_submission.id });
        setNotice("Stage evaluation refreshed.");
      } else {
        await evaluateSubmission({ submission_id: target.row.latest_submission.id, draft: false });
        setNotice("Final evaluation completed.");
      }
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to run the review evaluation."));
    } finally {
      setProcessing(false);
      setBusyStudentId(null);
      setBusyAction("");
    }
  };

  const handleDeleteStudent = async (student) => {
    const confirmed = window.confirm(
      `Delete ${student.name}? This permanently removes the student, submissions, evaluations, final marks records, uploaded files, vector data, and generated reports.`,
    );
    if (!confirmed) {
      return;
    }

    setProcessing(true);
    setBusyStudentId(student.id);
    setBusyAction("delete");
    setError("");
    setNotice("");

    try {
      const response = await deleteStudent(student.id);
      setNotice(response.message || `${student.name} deleted successfully.`);
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to delete the student."));
    } finally {
      setProcessing(false);
      setBusyStudentId(null);
      setBusyAction("");
    }
  };

  const rows = dashboard?.students || [];
  const rankings = dashboard?.rankings || [];
  const stageDefinitions = dashboard?.stage_definitions || [];
  const rubrics = dashboard?.rubrics || [];
  const continuousProgress = dashboard?.continuous_progress || [];
  const masterBrief = dashboard?.master_brief || null;
  const topEvaluation = getTopEvaluation(rows);

  const handleSaveStage = async (stageId, draft) => {
    setSavingStageId(stageId);
    setError("");
    setNotice("");

    try {
      await updateStage(stageId, {
        name: draft?.name || "Unnamed Stage",
        max_marks: Number(draft?.max_marks || 1),
      });
      setNotice("Continuous stage settings updated.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to update the stage settings."));
    } finally {
      setSavingStageId(null);
    }
  };

  const handleCreateStage = async (draft) => {
    setCreatingStage(true);
    setError("");
    setNotice("");

    try {
      await createStage({
        name: draft?.name || "New Stage",
        max_marks: Number(draft?.max_marks || 1),
      });
      setNotice("New stage added successfully.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to add a new stage."));
    } finally {
      setCreatingStage(false);
    }
  };

  const handleDeleteStage = async (stage) => {
    const confirmed = window.confirm(
      `Delete ${stage.name}? Only the last stage with no linked submissions can be removed.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingStageId(stage.id);
    setError("");
    setNotice("");

    try {
      const response = await deleteStage(stage.id);
      setNotice(response.message || "Stage deleted successfully.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to delete the stage."));
    } finally {
      setDeletingStageId(null);
    }
  };

  const handleSaveRubric = async (rubricId, draft) => {
    setSavingRubricId(rubricId);
    setError("");
    setNotice("");

    try {
      await updateRubric(rubricId, {
        name: draft?.name || "Unnamed Rubric",
        weight: Number(draft?.weight || 0),
        later_stage_only: Boolean(draft?.later_stage_only),
      });
      setNotice("Scoring rubric updated.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to update the scoring rubric."));
    } finally {
      setSavingRubricId(null);
    }
  };

  const handleCreateRubric = async (draft) => {
    setCreatingRubric(true);
    setError("");
    setNotice("");

    try {
      await createRubric({
        name: draft?.name || "New Rubric",
        weight: Number(draft?.weight || 0),
        later_stage_only: Boolean(draft?.later_stage_only),
      });
      setNotice("New scoring rubric added.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to add the scoring rubric."));
    } finally {
      setCreatingRubric(false);
    }
  };

  const handleDeleteRubric = async (rubric) => {
    const confirmed = window.confirm(
      `Delete the rubric "${rubric.name}"? Existing evaluations will keep their old snapshots, but future evaluations will stop using it.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingRubricId(rubric.id);
    setError("");
    setNotice("");

    try {
      const response = await deleteRubric(rubric.id);
      setNotice(response.message || "Rubric deleted successfully.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to delete the rubric."));
    } finally {
      setDeletingRubricId(null);
    }
  };

  const handleUploadMasterBrief = async ({ title, text, file }) => {
    setMasterBriefLoading(true);
    setError("");
    setNotice("");

    try {
      const formData = new FormData();
      if (title) {
        formData.append("title", title);
      }
      if (text) {
        formData.append("text", text);
      }
      if (file) {
        formData.append("file", file);
      }

      await uploadMasterBrief(formData);
      setNotice("Master brief uploaded. New evaluations will now be checked against the approved topic scope.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to upload the master brief."));
    } finally {
      setMasterBriefLoading(false);
    }
  };

  return (
    <Layout
      title="Teacher Dashboard"
      subtitle="Track every student submission, compare cumulative marks, launch evaluation, and finalize the class-wide marks ranking across the cohort."
      actions={
        <button type="button" className="action-button" onClick={handleFinalize} disabled={processing}>
          {processing ? "Processing..." : "Finalize marks ranking"}
        </button>
      }
    >
      {error ? <div className="rounded-3xl bg-rose-50 px-5 py-4 text-sm text-rose-600">{error}</div> : null}
      {notice ? <div className="rounded-3xl bg-emerald-50 px-5 py-4 text-sm text-emerald-700">{notice}</div> : null}

      {loading ? (
        <div className="section-shell text-sm text-slate-500">Loading dashboard...</div>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Students"
              value={dashboard?.statistics?.student_count || 0}
              hint="Students present in the current workspace."
            />
            <StatCard
              label="Evaluated"
              value={dashboard?.statistics?.evaluated_count || 0}
              hint="Rows with at least one draft or final score."
            />
            <StatCard
              label="Mean Marks"
              value={dashboard?.statistics?.mean_score || 0}
              hint="Current class-level average in marks."
            />
            <StatCard
              label="Top Marks"
              value={
                typeof dashboard?.statistics?.top_score === "number"
                  ? formatMarks(dashboard.statistics.top_score, dashboard?.statistics?.total_possible_marks)
                  : "Pending"
              }
              hint="Highest cumulative marks in the cohort right now."
            />
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <TeacherSubmissionTable
              rows={rows}
              onEvaluate={handleFinalEvaluation}
              onDelete={handleDeleteStudent}
              processing={processing}
              busyStudentId={busyStudentId}
              busyAction={busyAction}
            />
            <MarksComparisonChart rows={rows} meanScore={dashboard?.statistics?.mean_score} totalPossibleMarks={dashboard?.statistics?.total_possible_marks} />
          </section>

          <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <MasterBriefCard masterBrief={masterBrief} onUpload={handleUploadMasterBrief} loading={masterBriefLoading} />
            <StageSettingsCard
              stages={stageDefinitions}
              onSave={handleSaveStage}
              onCreate={handleCreateStage}
              onDelete={handleDeleteStage}
              savingStageId={savingStageId}
              deletingStageId={deletingStageId}
              creatingStage={creatingStage}
            />
          </section>

          <section className="grid gap-6 xl:grid-cols-[1fr]">
            <RubricSettingsCard
              rubrics={rubrics}
              onSave={handleSaveRubric}
              onCreate={handleCreateRubric}
              onDelete={handleDeleteRubric}
              savingRubricId={savingRubricId}
              deletingRubricId={deletingRubricId}
              creatingRubric={creatingRubric}
            />
          </section>

          <section className="grid gap-6 xl:grid-cols-[1fr]">
            <ContinuousProgressTable rows={continuousProgress} feedbackBasePath="/teacher/stage-feedback" />
          </section>

          <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
            {topEvaluation ? (
              <ScoreBreakdownChart evaluation={topEvaluation} />
            ) : (
              <div className="section-shell text-sm text-slate-500">
                Once a legacy final evaluation exists, the highest current score will appear here.
              </div>
            )}

            <div className="section-shell">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-ink">Rank List</h2>
                <p className="mt-2 text-sm text-slate-600">Final standings after marks are summed across stages and ranked across the class.</p>
              </div>

              <div className="space-y-3">
                {rankings.length ? (
                  rankings.map((item) => (
                    <div
                      key={item.student.id}
                      className="flex flex-wrap items-center justify-between gap-4 rounded-3xl border border-slate-200 bg-slate-50/70 px-5 py-4"
                    >
                      <div>
                        <p className="text-lg font-bold text-ink">
                          #{item.final_marks.rank} {item.student.name}
                        </p>
                        <p className="text-sm text-slate-500">{item.submission.title}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-extrabold text-accent">
                          {formatMarks(item.final_marks?.earned, item.final_marks?.possible)}
                        </p>
                        <p className="text-sm text-slate-500">
                          Avg {formatMarks(item.comparison?.class_average, item.comparison?.total_possible_marks)} | Top {formatMarks(item.comparison?.top_score, item.comparison?.total_possible_marks)}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-3xl border border-dashed border-slate-300 px-5 py-8 text-sm text-slate-500">
                    Finalize marks ranking to populate the rank list.
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="grid gap-6 xl:grid-cols-[1fr]">
            <StageMarksMatrix rows={rows} stages={stageDefinitions} feedbackBasePath="/teacher/stage-feedback" />
          </section>
        </>
      )}
    </Layout>
  );
}
