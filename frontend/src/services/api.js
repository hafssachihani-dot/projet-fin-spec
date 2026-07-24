import {
  clearLocalSession,
  isAuthSessionError,
  refreshCurrentSession,
} from "./supabase";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8020";

function getApiError(payload, status) {
  const detail = payload?.detail ?? payload?.message ?? payload ?? "Erreur API";
  const message = typeof detail === "string" ? detail : JSON.stringify(detail);
  const error = new Error(message);
  error.status = status;
  error.code = payload?.error_code || payload?.code || "";
  return error;
}

function hasAuthorization(options) {
  return Boolean(new Headers(options.headers || {}).get("Authorization"));
}

async function recoverAuthorization(options) {
  const refreshedSession = await refreshCurrentSession();
  if (!refreshedSession?.access_token) return null;

  window.dispatchEvent(new CustomEvent("auth-session-refreshed", { detail: refreshedSession }));
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${refreshedSession.access_token}`);
  return { ...options, headers };
}

async function expireFrontendSession() {
  await clearLocalSession();
  window.dispatchEvent(new CustomEvent("auth-session-expired"));
}

async function fetchWithSessionRecovery(path, options = {}) {
  let activeOptions = options;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    let response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, activeOptions);
    } catch {
      throw new Error(
        `Impossible de contacter le backend (${API_BASE_URL}). Verifie que FastAPI est lance a cette adresse.`
      );
    }

    if (response.ok) return response;

    const payload = await response.json().catch(async () => ({
      detail: await response.text().catch(() => "Erreur inconnue"),
    }));
    const error = getApiError(payload, response.status);
    const authFailure = response.status === 401 || response.status === 403 || isAuthSessionError(error);

    if (attempt === 0 && authFailure && hasAuthorization(activeOptions)) {
      try {
        const recoveredOptions = await recoverAuthorization(activeOptions);
        if (recoveredOptions) {
          activeOptions = recoveredOptions;
          continue;
        }
      } catch (refreshError) {
        if (!isAuthSessionError(refreshError) && refreshError.code !== "AUTH_SESSION_EXPIRED") {
          throw refreshError;
        }
      }

      await expireFrontendSession();
      const sessionError = new Error("Ta session a expire. Reconnecte-toi pour continuer.");
      sessionError.code = "AUTH_SESSION_EXPIRED";
      throw sessionError;
    }

    throw error;
  }

  throw new Error("Erreur API");
}

async function request(path, options = {}) {
  const response = await fetchWithSessionRecovery(path, options);
  return response.json();
}

async function requestBlob(path, options = {}) {
  const response = await fetchWithSessionRecovery(path, options);
  return response.blob();
}

export function listKnowledgeBases() {
  return request("/api/knowledge-bases");
}

export function createKnowledgeBase({ name, subject, files, token }) {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("subject", subject);
  files.forEach((file) => formData.append("files", file));

  return request("/api/knowledge-bases", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData
  });
}

export function generateExam(payload) {
  return request("/api/exams/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export function createManagedUser(token, payload) {
  return request("/api/admin/users", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export function listProfiles(token) {
  return request("/api/admin/profiles", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function updateProfile(token, profileId, payload) {
  return request(`/api/admin/profiles/${profileId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export function deleteProfile(token, profileId) {
  return request(`/api/admin/profiles/${profileId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function launchPedagogicalReport(token, payload) {
  return request("/api/admin/pedagogical-reports", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export function listAgenda(token) {
  return request("/api/agenda", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function createAgenda(token, payload) {
  return request("/api/agenda", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export function listClassResources(token) {
  return request("/api/resources", {
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function uploadClassResource(token, { title, description, targetStudyLevel, file }) {
  const formData = new FormData();
  formData.append("title", title);
  formData.append("description", description || "");
  formData.append("target_study_level", targetStudyLevel);
  formData.append("file", file);

  return request("/api/staff/resources", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData
  });
}

export function deleteClassResource(token, resourceId) {
  return request(`/api/staff/resources/${resourceId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function fetchClassResourceBlob(token, resourceId) {
  return requestBlob(`/api/resources/${resourceId}/file`, {
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function publishGeneratedExam(token, payload) {
  return request("/api/exams/publish", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export function listPublishedExams(token) {
  return request("/api/exams/published", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function deletePublishedExam(token, examId) {
  return request(`/api/exams/published/${examId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function updatePublishedExamVisibility(token, examId, status) {
  return request(`/api/exams/published/${examId}/visibility`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ status })
  });
}

export function updatePublishedExam(token, examId, payload) {
  return request(`/api/exams/published/${examId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export function reviewExamApproval(token, examId, decision, reason = "") {
  return request(`/api/admin/exams/${examId}/approval`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ decision, reason })
  });
}

export function submitStudentAttempt(token, payload) {
  return request("/api/student/attempts/submit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export function listStudentAttempts(token) {
  return request("/api/student/attempts", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function listStaffResults(token, studyLevel = "") {
  const query = studyLevel ? `?study_level=${encodeURIComponent(studyLevel)}` : "";
  return request(`/api/staff/results${query}`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function getStaffDashboard(token, studyLevel, academicYear) {
  const query = new URLSearchParams({
    study_level: studyLevel,
    academic_year: academicYear
  });
  return request(`/api/staff/dashboard?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function getAgentTelemetryDashboard(token, periodDays = 30) {
  return request(`/api/telemetry/dashboard?period_days=${encodeURIComponent(periodDays)}`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function getLatestWorkflowResult() {
  return request("/api/workflow/latest-result");
}

export function clearLatestWorkflowResult() {
  return request("/api/workflow/latest-result", {
    method: "DELETE"
  });
}
