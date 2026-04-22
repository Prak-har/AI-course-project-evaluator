import { useEffect, useState } from "react";

import { deleteStageSubmission, getStudentDashboard, uploadStageProgress } from "../api/client";
import ContinuousProgressTimeline from "../components/ContinuousProgressTimeline";
import ContinuousUploadCard from "../components/ContinuousUploadCard";
import FeedbackFocusPanel from "../components/FeedbackFocusPanel";
import Layout from "../components/Layout";
import StageMarksBreakdown from "../components/StageMarksBreakdown";
import StatCard from "../components/StatCard";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../utils/errors";

function getLatestStageSubmission(projects) {
  const stageSubmissions = (projects || []).flatMap((project) => project.stage_submissions || []);
  if (!stageSubmissions.length) {
    return null;
  }
  return [...stageSubmissions].sort((left, right) => new Date(right.created_at) - new Date(left.created_at))[0];
}

function getLatestStageEvaluation(projects) {
  const evaluations = (projects || [])
    .flatMap((project) => project.stage_submissions || [])
    .flatMap((submission) => submission.evaluations || []);
  if (!evaluations.length) {
    return null;
  }
  return [...evaluations].sort((left, right) => new Date(right.created_at) - new Date(left.created_at))[0];
}

function countStageSubmissions(projects) {
  return (projects || []).reduce((total, project) => total + (project.stage_submissions?.length || 0), 0);
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

export default function StudentDashboard() {
  const { user, isReady } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stageUploading, setStageUploading] = useState(false);
  const [deletingStageId, setDeletingStageId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadDashboard = async () => {
    if (!user?.id) {
      setDashboard(null);
      setLoading(false);
      setError("Please sign in again to load your dashboard.");
      return;
    }

    setLoading(true);
    try {
      const response = await getStudentDashboard(user.id);
      setDashboard(response);
      setError("");
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to load student dashboard."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isReady) {
      return;
    }
    loadDashboard();
  }, [isReady, user?.id]);

  const handleStageUpload = async ({ projectTitle, stageId, text, file }) => {
    setStageUploading(true);
    setError("");
    setNotice("");

    try {
      const formData = new FormData();
      formData.append("student_id", String(user.id));
      formData.append("project_title", projectTitle);
      formData.append("stage_id", String(stageId));
      if (text) {
        formData.append("text", text);
      }
      if (file) {
        formData.append("file", file);
      }

      const response = await uploadStageProgress(formData);
      setNotice(
        response.embedded
          ? "Stage submission saved and evaluated successfully."
          : response.warning || "Stage submission was saved, but the evaluation could not run yet.",
      );
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to submit the stage progress."));
    } finally {
      setStageUploading(false);
    }
  };

  const handleDeleteStage = async (stageSubmission) => {
    const confirmed = window.confirm(
      `Delete this ${stageSubmission.stage?.name || "stage"} submission? This permanently removes the stage upload and its evaluation.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingStageId(stageSubmission.id);
    setError("");
    setNotice("");
    try {
      const response = await deleteStageSubmission(stageSubmission.id, user.id);
      setNotice(response.message || "Stage submission deleted successfully.");
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to delete the stage submission."));
    } finally {
      setDeletingStageId(null);
    }
  };

  const progressProjects = dashboard?.student?.progress_projects || [];
  const stageDefinitions = dashboard?.stage_definitions || [];
  const latestStageSubmission = getLatestStageSubmission(progressProjects);
  const latestStageEvaluation = getLatestStageEvaluation(progressProjects);
  const finalMarks = dashboard?.final_marks || null;
  const comparison = dashboard?.comparison || null;
  const stageBreakdown = dashboard?.stage_breakdown || [];

  return (
    <Layout
      title="Student Dashboard"
      subtitle="Submit your project stage by stage, keep earlier checkpoints as context, and track whether your latest work is closing the feedback gaps from earlier stages."
    >
      {error ? <div className="rounded-3xl bg-rose-50 px-5 py-4 text-sm text-rose-600">{error}</div> : null}
      {notice ? <div className="rounded-3xl bg-amber-50 px-5 py-4 text-sm text-amber-700">{notice}</div> : null}

      {loading ? (
        <div className="section-shell text-sm text-slate-500">Loading dashboard...</div>
      ) : !dashboard?.student ? (
        <div className="section-shell text-sm text-slate-500">
          Your dashboard data is not available yet. Sign out and sign back in once if this persists.
        </div>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <StatCard
              label="Projects"
              value={progressProjects.length}
              hint="Distinct project tracks under continuous evaluation."
            />
            <StatCard
              label="Stage Uploads"
              value={countStageSubmissions(progressProjects)}
              hint="Every stage checkpoint stays in your progress history."
            />
            <StatCard
              label="Latest Stage"
              value={latestStageEvaluation ? `${latestStageEvaluation.scaled_score}/${latestStageEvaluation.max_marks}` : "Pending"}
              hint="Most recent scaled score from the stage workflow."
            />
            <StatCard
              label="Final Marks"
              value={formatMarks(finalMarks?.earned, finalMarks?.possible)}
              hint="Summed marks from the latest evaluated submission in each stage."
            />
            <StatCard
              label="Class Rank"
              value={comparison?.rank ? `#${comparison.rank}/${comparison.ranked_count}` : "Pending"}
              hint="Visible after the teacher finalizes the class-wide marks comparison."
            />
            <StatCard
              label="Class Average"
              value={formatMarks(comparison?.class_average, comparison?.total_possible_marks || finalMarks?.possible)}
              hint="Where your current marks sit against the current cohort average."
            />
          </section>

          <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <ContinuousUploadCard stages={stageDefinitions} projects={progressProjects} onUpload={handleStageUpload} loading={stageUploading} />
            <FeedbackFocusPanel
              evaluation={latestStageEvaluation}
              title="Latest Stage Feedback"
              subtitle={
                latestStageSubmission
                  ? `Visible focus areas from your latest checkpoint in ${latestStageSubmission.stage?.name || "the current stage"}.`
                  : "Submit a stage checkpoint to surface the current strong areas and next actions."
              }
              action={
                latestStageSubmission ? (
                  <a
                    href={`/student/stage-feedback/${latestStageSubmission.id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="muted-button"
                  >
                    Open full feedback
                  </a>
                ) : null
              }
            />
          </section>

          <StageMarksBreakdown stages={stageDefinitions} breakdown={stageBreakdown} finalMarks={finalMarks} feedbackBasePath="/student/stage-feedback" />

          <ContinuousProgressTimeline
            projects={progressProjects}
            onDelete={handleDeleteStage}
            deletingStageId={deletingStageId}
            feedbackBasePath="/student/stage-feedback"
          />
        </>
      )}
    </Layout>
  );
}
