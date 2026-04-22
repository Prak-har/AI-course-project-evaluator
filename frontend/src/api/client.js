import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export async function login(payload) {
  const response = await api.post("/auth/login", payload);
  return response.data;
}

export async function uploadProject(formData) {
  const response = await api.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function evaluateSubmission(payload) {
  const response = await api.post("/evaluate", payload);
  return response.data;
}

export async function uploadStageProgress(formData) {
  const response = await api.post("/continuous/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function evaluateStageProgress(payload) {
  const response = await api.post("/continuous/evaluate", payload);
  return response.data;
}

export async function getStageFeedback(stageSubmissionId) {
  const response = await api.get(`/continuous/stage-submission/${stageSubmissionId}`);
  return response.data;
}

export async function getStudentDashboard(studentId) {
  const response = await api.get(`/student/${studentId}`);
  return response.data;
}

export async function getTeacherDashboard() {
  const response = await api.get("/teacher/dashboard");
  return response.data;
}

export async function finalizeGrades() {
  const response = await api.post("/finalize");
  return response.data;
}

export async function deleteStudent(studentId) {
  const response = await api.delete(`/teacher/student/${studentId}`);
  return response.data;
}

export async function deleteStageSubmission(stageSubmissionId, studentId) {
  const response = await api.delete(`/continuous/stage-submission/${stageSubmissionId}`, {
    params: {
      student_id: studentId,
    },
  });
  return response.data;
}

export async function uploadMasterBrief(formData) {
  const response = await api.post("/teacher/master-brief", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function updateStage(stageId, payload) {
  const response = await api.put(`/teacher/stages/${stageId}`, payload);
  return response.data;
}

export async function createStage(payload) {
  const response = await api.post("/teacher/stages", payload);
  return response.data;
}

export async function deleteStage(stageId) {
  const response = await api.delete(`/teacher/stages/${stageId}`);
  return response.data;
}

export async function createRubric(payload) {
  const response = await api.post("/teacher/rubrics", payload);
  return response.data;
}

export async function updateRubric(rubricId, payload) {
  const response = await api.put(`/teacher/rubrics/${rubricId}`, payload);
  return response.data;
}

export async function deleteRubric(rubricId) {
  const response = await api.delete(`/teacher/rubrics/${rubricId}`);
  return response.data;
}

export function downloadReportUrl(submissionId) {
  return `${api.defaults.baseURL}/teacher/report/${submissionId}`;
}
