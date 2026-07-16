const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8010";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch (error) {
    throw new Error(
      `Impossible de contacter le backend (${API_BASE_URL}). Verifie que FastAPI est lance sur le port 8010.`
    );
  }

  if (!response.ok) {
    const payload = await response.json().catch(async () => ({
      detail: await response.text().catch(() => "Erreur inconnue"),
    }));
    throw new Error(payload.detail || "Erreur API");
  }
  return response.json();
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

export function getLatestWorkflowResult() {
  return request("/api/workflow/latest-result");
}

export function clearLatestWorkflowResult() {
  return request("/api/workflow/latest-result", {
    method: "DELETE"
  });
}
