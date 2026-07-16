<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import {
  BarChart3,
  BookOpenCheck,
  CalendarDays,
  Eye,
  EyeOff,
  FileText,
  Library,
  NotebookPen,
  Pencil,
  PlayCircle,
  Save,
  Sparkles,
  Trash2,
  UserPlus,
  UsersRound,
  X,
} from "lucide-vue-next";
import AuthPanel from "./components/AuthPanel.vue";
import AdminStudentManager from "./components/AdminStudentManager.vue";
import AppSidebar from "./components/AppSidebar.vue";
import AppTopbar from "./components/AppTopbar.vue";
import KnowledgeBaseUploader from "./components/KnowledgeBaseUploader.vue";
import ExamGenerationForm from "./components/ExamGenerationForm.vue";
import ExamDraftPreview from "./components/ExamDraftPreview.vue";
import WorkflowResult from "./components/WorkflowResult.vue";
import {
  clearLatestWorkflowResult,
  createAgenda,
  deletePublishedExam,
  deleteProfile,
  generateExam,
  getLatestWorkflowResult,
  listAgenda,
  listKnowledgeBases,
  listPublishedExams,
  listProfiles,
  publishGeneratedExam,
  updateProfile,
  updatePublishedExamVisibility,
} from "./services/api";
import {
  getCurrentProfile,
  getCurrentSession,
  signOut,
} from "./services/supabase";

const knowledgeBases = ref([]);
const selectedKnowledgeBaseId = ref("");
const workflowRun = ref(null);
const draftExam = ref(null);
const lastExamForm = ref(null);
const publishedExams = ref([]);
const isGenerating = ref(false);
const isPublishingExam = ref(false);
const isWaitingForCallback = ref(false);
const errorMessage = ref("");
const publishMessage = ref("");
const generationMessage = ref("");
const activePage = ref("dashboard");
const isSidebarExpanded = ref(false);
const agendaItems = ref([]);
const agendaMessage = ref("");
const isSavingAgenda = ref(false);
const adminProfiles = ref([]);
const adminMessage = ref("");
const isLoadingProfiles = ref(false);
const selectedTeacherExam = ref(null);
const selectedStudentExam = ref(null);
const studentAnswers = ref({});
const studentExamMessage = ref("");

const authLoading = ref(true);
const session = ref(null);
const profile = ref(null);
const showAdminModal = ref(false);

const studyLevels = ["Licence 1", "Licence 2", "Licence 3", "Master 1", "Master 2"];

const agendaForm = reactive({
  title: "",
  target_study_level: "Licence 2",
  evaluation_type: "Controle continu",
  scheduled_at: "",
  description: "",
});

const displayRole = computed(() =>
  profile.value?.role || session.value?.user?.user_metadata?.role || "unknown"
);

const displayName = computed(() =>
  profile.value?.full_name || session.value?.user?.user_metadata?.full_name || session.value?.user?.email
);

const displayStudyLevel = computed(() =>
  profile.value?.study_level || session.value?.user?.user_metadata?.study_level || ""
);

const isAdmin = computed(() => displayRole.value === "admin");
const isStudent = computed(() => displayRole.value === "student");
const canManagePedagogy = computed(() => displayRole.value === "teacher" || displayRole.value === "admin");

const navigationItems = computed(() => {
  if (isStudent.value) {
    return [
      { key: "student-exams", label: "Mes examens", icon: BookOpenCheck },
      { key: "student-notes", label: "Notes", icon: NotebookPen },
      { key: "agenda", label: "Agenda", icon: CalendarDays },
    ];
  }

  const items = [{ key: "dashboard", label: "Dashboard", icon: BarChart3 }];

  if (canManagePedagogy.value) {
    items.push({ key: "create-exam", label: "Creer examen", icon: Sparkles });
    items.push({ key: "teacher-exams", label: "Mes examens", icon: BookOpenCheck });
  }

  items.push({ key: "agenda", label: "Agenda", icon: CalendarDays });
  items.push({ key: "workflow", label: "Workflow", icon: FileText });

  if (isAdmin.value) {
    items.push({ key: "administration", label: "Administration", icon: UsersRound });
  }

  return items;
});

const dashboardCards = computed(() => [
  isStudent.value
    ? { label: "Examens disponibles", value: studentPublishedExams.value.length, tone: "cyan" }
    : { label: "Supports PDF", value: knowledgeBases.value.length, tone: "cyan" },
  { label: "Evenements agenda", value: agendaItems.value.length, tone: "purple" },
  isStudent.value
    ? { label: "Notes publiees", value: 0, tone: "green" }
    : { label: "Role courant", value: displayRole.value, tone: "green" },
  isStudent.value
    ? { label: "Niveau", value: displayStudyLevel.value || "-", tone: "mint" }
    : { label: "Webhook", value: workflowRun.value?.status || "pret", tone: "mint" },
]);

const pageTitle = computed(() => {
  const labels = {
    dashboard: "Dashboard",
    "student-exams": "Mes examens",
    "student-notes": "Notes",
    "create-exam": "Creer examen",
    "teacher-exams": "Mes examens",
    agenda: "Agenda",
    administration: "Administration",
    workflow: "Workflow",
  };
  return labels[activePage.value] || "Workflow";
});

const pageSubtitle = computed(() =>
  isStudent.value
    ? `Espace etudiant${displayStudyLevel.value ? ` - ${displayStudyLevel.value}` : ""}`
    : "Espace pedagogique et orchestration Agentic RAG"
);

const selectedKnowledgeBase = computed(() =>
  knowledgeBases.value.find((item) => item.id === selectedKnowledgeBaseId.value)
);

const latestAgendaItems = computed(() => agendaItems.value.slice(0, 3));

const studentPublishedExams = computed(() => publishedExams.value);

function formatDateTime(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function examRecordPayload(record) {
  return record?.exam || record || {};
}

function examRecordTitle(record) {
  const exam = examRecordPayload(record);
  return record?.title || exam.module || "Examen";
}

function examQuestions(record) {
  return examRecordPayload(record).questions || [];
}

function questionText(question) {
  return question.texte || question.enonce || question.prompt || "";
}

function questionChoices(question) {
  const choices = question.choix || question.options || question.propositions || question.answers || [];
  if (Array.isArray(choices) && choices.length) return choices;

  // Pour Vrai/Faux, l'agent peut oublier les choix. On les affiche quand meme.
  const type = String(question.type || "").toLowerCase();
  if (type.includes("vrai") || type.includes("faux")) {
    return ["Vrai", "Faux"];
  }

  return [];
}

function unwrapWorkflowPayload(value) {
  if (!value) return null;

  if (typeof value === "string") {
    const trimmedValue = value.trim();
    try {
      return unwrapWorkflowPayload(JSON.parse(trimmedValue));
    } catch {
      const objectStart = trimmedValue.indexOf("{");
      const objectEnd = trimmedValue.lastIndexOf("}");
      if (objectStart >= 0 && objectEnd > objectStart) {
        try {
          return unwrapWorkflowPayload(JSON.parse(trimmedValue.slice(objectStart, objectEnd + 1)));
        } catch {
          return trimmedValue;
        }
      }
      return trimmedValue;
    }
  }

  if (value.payload) {
    return unwrapWorkflowPayload(value.payload);
  }

  if (value.text) {
    return typeof value.text === "string" ? unwrapWorkflowPayload(value.text) || value.text : value.text;
  }

  return value;
}

function findExamWithQuestions(value, visited = new Set()) {
  const unwrappedValue = unwrapWorkflowPayload(value);

  if (!unwrappedValue || typeof unwrappedValue !== "object") {
    return null;
  }

  if (visited.has(unwrappedValue)) {
    return null;
  }
  visited.add(unwrappedValue);

  if (Array.isArray(unwrappedValue)) {
    for (const item of unwrappedValue) {
      const found = findExamWithQuestions(item, visited);
      if (found) return found;
    }
    return null;
  }

  if (Array.isArray(unwrappedValue.questions)) {
    return unwrappedValue;
  }

  for (const key of ["exam", "data", "text", "payload", "result", "response", "output", "outputs"]) {
    if (unwrappedValue[key]) {
      const found = findExamWithQuestions(unwrappedValue[key], visited);
      if (found) return found;
    }
  }

  for (const item of Object.values(unwrappedValue)) {
    const found = findExamWithQuestions(item, visited);
    if (found) return found;
  }

  return null;
}

function extractGeneratedExam(workflowResponse) {
  return findExamWithQuestions(workflowResponse);
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function waitForWorkflowCallback(maxAttempts = 40, delayMs = 3000) {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    generationMessage.value = `Workflow lance. Attente du resultat final (${attempt}/${maxAttempts})...`;
    const latestResult = await getLatestWorkflowResult();
    const exam = extractGeneratedExam(latestResult);
    if (exam) {
      return exam;
    }
    await wait(delayMs);
  }
  return null;
}

async function refreshKnowledgeBases() {
  knowledgeBases.value = await listKnowledgeBases();
  if (!selectedKnowledgeBaseId.value && knowledgeBases.value.length > 0) {
    selectedKnowledgeBaseId.value = knowledgeBases.value[0].id;
  }
}

async function refreshAgendaItems() {
  try {
    if (!session.value?.access_token) {
      agendaItems.value = [];
      return;
    }
    agendaItems.value = await listAgenda(session.value.access_token);
  } catch (error) {
    agendaItems.value = [];
    agendaMessage.value = error.message;
  }
}

async function refreshPublishedExams() {
  try {
    if (!session.value?.access_token) {
      publishedExams.value = [];
      return;
    }
    publishedExams.value = await listPublishedExams(session.value.access_token);
  } catch (error) {
    publishedExams.value = [];
    if (isStudent.value) {
      errorMessage.value = error.message;
    }
  }
}

function handleSidebarNavigate(page) {
  activePage.value = page;
  if (page === "teacher-exams" || page === "student-exams") {
    refreshPublishedExams();
  }
}

async function refreshAdminProfiles() {
  if (!isAdmin.value || !session.value?.access_token) {
    adminProfiles.value = [];
    return;
  }

  isLoadingProfiles.value = true;
  adminMessage.value = "";
  try {
    adminProfiles.value = await listProfiles(session.value.access_token);
  } catch (error) {
    adminMessage.value = error.message;
  } finally {
    isLoadingProfiles.value = false;
  }
}

async function loadAuthenticatedUser(activeSession) {
  session.value = activeSession;
  if (activeSession?.user?.id) {
    profile.value = await getCurrentProfile(activeSession.user.id);
  }
  await refreshKnowledgeBases();
  await refreshAgendaItems();
  await refreshPublishedExams();
  await refreshAdminProfiles();
  if (isStudent.value && activePage.value === "dashboard") {
    activePage.value = "student-exams";
  }
}

async function handleAuthenticated(activeSession) {
  errorMessage.value = "";
  try {
    await loadAuthenticatedUser(activeSession);
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function handleSignOut() {
  await signOut();
  session.value = null;
  profile.value = null;
  knowledgeBases.value = [];
  agendaItems.value = [];
  adminProfiles.value = [];
  publishedExams.value = [];
  selectedKnowledgeBaseId.value = "";
  workflowRun.value = null;
  draftExam.value = null;
  lastExamForm.value = null;
}

function handleKnowledgeBaseCreated(kb) {
  knowledgeBases.value = [kb, ...knowledgeBases.value.filter((item) => item.id !== kb.id)];
  selectedKnowledgeBaseId.value = kb.id;
}

async function handleGenerate(form) {
  errorMessage.value = "";
  publishMessage.value = "";
  generationMessage.value = "";
  workflowRun.value = null;
  draftExam.value = null;
  lastExamForm.value = { ...form };

  if (!selectedKnowledgeBaseId.value) {
    errorMessage.value = "Importe un PDF ou choisis une base avant de lancer le workflow.";
    activePage.value = "create-exam";
    return;
  }

  isGenerating.value = true;
  try {
    await clearLatestWorkflowResult();
    workflowRun.value = await generateExam({
      ...form,
      knowledge_base_id: selectedKnowledgeBaseId.value,
    });
    draftExam.value = extractGeneratedExam(workflowRun.value.workflow_response);
    if (!draftExam.value) {
      isWaitingForCallback.value = true;
      draftExam.value = await waitForWorkflowCallback();
    }
    activePage.value = "create-exam";
    if (!draftExam.value) {
      errorMessage.value = "Le workflow a ete lance, mais aucune liste de questions n'a ete recue avant la fin de l'attente. Verifie que l'API Request final pointe vers ton URL ngrok /api/workflow/callback.";
    } else {
      generationMessage.value = "Questions recues. L'enseignant peut verifier le brouillon.";
    }
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isGenerating.value = false;
    isWaitingForCallback.value = false;
  }
}

async function handleRegenerateExam() {
  if (!lastExamForm.value) return;
  await handleGenerate(lastExamForm.value);
}

async function handlePublishGeneratedExam() {
  if (!draftExam.value || !session.value?.access_token) return;

  isPublishingExam.value = true;
  publishMessage.value = "";
  errorMessage.value = "";

  try {
    await publishGeneratedExam(session.value.access_token, {
      exam: draftExam.value,
      target_study_level: draftExam.value.niveau || draftExam.value.study_level || lastExamForm.value?.study_level || "Licence 2",
      teacher_note: "Examen valide par l'enseignant.",
    });
    await refreshPublishedExams();
    publishMessage.value = "Examen publie. Les etudiants du niveau cible peuvent maintenant le voir.";
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isPublishingExam.value = false;
  }
}

function handleEditPublishedExam(record) {
  draftExam.value = examRecordPayload(record);
  publishMessage.value = "Brouillon charge depuis Mes examens. Tu peux verifier puis republier.";
  selectedTeacherExam.value = null;
  activePage.value = "create-exam";
}

async function handleDeletePublishedExam(record) {
  if (!session.value?.access_token) return;
  const confirmed = window.confirm(`Supprimer "${examRecordTitle(record)}" ? Il disparaitra aussi chez les etudiants.`);
  if (!confirmed) return;

  try {
    await deletePublishedExam(session.value.access_token, record.id);
    selectedTeacherExam.value = null;
    await refreshPublishedExams();
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function handleToggleExamVisibility(record) {
  if (!session.value?.access_token) return;
  const nextStatus = record.status === "published" ? "hidden" : "published";

  try {
    const updated = await updatePublishedExamVisibility(session.value.access_token, record.id, nextStatus);
    publishedExams.value = publishedExams.value.map((item) => (item.id === updated.id ? updated : item));
    selectedTeacherExam.value = updated;
  } catch (error) {
    errorMessage.value = error.message;
  }
}

function openTeacherExam(record) {
  selectedTeacherExam.value = record;
}

function closeTeacherExam() {
  selectedTeacherExam.value = null;
}

function openStudentExam(record) {
  selectedStudentExam.value = record;
  studentAnswers.value = {};
  studentExamMessage.value = "";
}

function closeStudentExam() {
  selectedStudentExam.value = null;
  studentAnswers.value = {};
  studentExamMessage.value = "";
}

function submitStudentExam() {
  // POC: on garde les reponses cote interface. Le workflow de correction viendra apres.
  studentExamMessage.value = "Reponses enregistrees localement. Prochaine etape: envoyer vers le workflow de correction.";
}

async function handleCreateAgendaItem() {
  agendaMessage.value = "";
  if (!agendaForm.title || !agendaForm.scheduled_at || !agendaForm.target_study_level) {
    agendaMessage.value = "Ajoute un titre, une date et un niveau.";
    return;
  }

  isSavingAgenda.value = true;
  try {
    await createAgenda(session.value.access_token, {
      title: agendaForm.title,
      description: agendaForm.description,
      target_study_level: agendaForm.target_study_level,
      evaluation_type: agendaForm.evaluation_type,
      scheduled_at: new Date(agendaForm.scheduled_at).toISOString(),
    });
    agendaForm.title = "";
    agendaForm.description = "";
    agendaForm.evaluation_type = "Controle continu";
    agendaForm.scheduled_at = "";
    await refreshAgendaItems();
    agendaMessage.value = "Evenement ajoute dans l'agenda.";
  } catch (error) {
    agendaMessage.value = error.message;
  } finally {
    isSavingAgenda.value = false;
  }
}

async function handleSaveProfile(row) {
  adminMessage.value = "";
  try {
    const updated = await updateProfile(session.value.access_token, row.id, {
      full_name: row.full_name,
      role: row.role,
      study_level: row.role === "student" ? row.study_level : null,
    });
    adminProfiles.value = adminProfiles.value.map((item) => (item.id === updated.id ? updated : item));
    adminMessage.value = "Profil mis a jour.";
  } catch (error) {
    adminMessage.value = error.message;
  }
}

async function handleDeleteProfile(row) {
  adminMessage.value = "";
  const confirmed = window.confirm(`Supprimer le profil ${row.full_name || row.id} ?`);
  if (!confirmed) return;

  try {
    await deleteProfile(session.value.access_token, row.id);
    adminProfiles.value = adminProfiles.value.filter((item) => item.id !== row.id);
    adminMessage.value = "Profil supprime.";
  } catch (error) {
    adminMessage.value = error.message;
  }
}

async function handleAdminModalClose() {
  showAdminModal.value = false;
  await refreshAdminProfiles();
}

onMounted(async () => {
  try {
    const activeSession = await getCurrentSession();
    if (activeSession) {
      await loadAuthenticatedUser(activeSession);
    }
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    authLoading.value = false;
  }
});
</script>

<template>
  <AuthPanel v-if="!authLoading && !session" @authenticated="handleAuthenticated" />

  <main v-if="authLoading" class="app-shell">
    <section class="panel loading-panel">Chargement de la session...</section>
  </main>

  <main
    v-else-if="session"
    class="dashboard-shell"
    :class="{ 'sidebar-expanded': isSidebarExpanded }"
  >
    <AppSidebar
      :items="navigationItems"
      :active-page="activePage"
      :display-name="displayName"
      :display-role="displayRole"
      @navigate="handleSidebarNavigate"
      @expand="isSidebarExpanded = $event"
    />

    <section class="dashboard-main">
      <AppTopbar
        :title="pageTitle"
        :subtitle="pageSubtitle"
        :display-role="displayRole"
        :display-name="displayName"
        :is-admin="isAdmin"
        @create-user="showAdminModal = true"
        @sign-out="handleSignOut"
      />

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <AdminStudentManager
        v-if="isAdmin && showAdminModal"
        :access-token="session.access_token"
        @close="handleAdminModalClose"
      />

      <div v-if="selectedTeacherExam" class="modal-backdrop" @click.self="closeTeacherExam">
        <section class="admin-modal exam-manager-modal">
          <div class="modal-header">
            <div>
              <span class="eyebrow">ENSEIGNANT</span>
              <h2>{{ examRecordTitle(selectedTeacherExam) }}</h2>
            </div>
            <button class="icon-button" type="button" aria-label="Fermer" @click="closeTeacherExam">
              <X :size="18" />
            </button>
          </div>

          <div class="exam-detail-summary">
            <span class="status-pill" :class="{ success: selectedTeacherExam.status === 'published' }">
              {{ selectedTeacherExam.status === "published" ? "Visible etudiant" : "Cache aux etudiants" }}
            </span>
            <span>{{ selectedTeacherExam.evaluation_type }} - {{ selectedTeacherExam.target_study_level }}</span>
            <span>{{ examQuestions(selectedTeacherExam).length }} questions</span>
          </div>

          <div class="exam-modal-preview">
            <article v-for="(question, index) in examQuestions(selectedTeacherExam).slice(0, 4)" :key="question.numero || index">
              <strong>Question {{ question.numero || index + 1 }}</strong>
              <p>{{ questionText(question) }}</p>
            </article>
            <p v-if="examQuestions(selectedTeacherExam).length > 4" class="helper-text">
              + {{ examQuestions(selectedTeacherExam).length - 4 }} autres questions.
            </p>
          </div>

          <div class="draft-actions">
            <button class="btn btn-secondary" type="button" @click="handleEditPublishedExam(selectedTeacherExam)">
              <Pencil :size="18" />
              <span>Modifier</span>
            </button>
            <button class="btn btn-secondary" type="button" @click="handleToggleExamVisibility(selectedTeacherExam)">
              <EyeOff v-if="selectedTeacherExam.status === 'published'" :size="18" />
              <Eye v-else :size="18" />
              <span>{{ selectedTeacherExam.status === "published" ? "Cacher" : "Afficher" }}</span>
            </button>
            <button class="btn btn-danger" type="button" @click="handleDeletePublishedExam(selectedTeacherExam)">
              <Trash2 :size="18" />
              <span>Supprimer</span>
            </button>
          </div>
        </section>
      </div>

      <div v-if="selectedStudentExam" class="modal-backdrop" @click.self="closeStudentExam">
        <section class="admin-modal exam-take-modal">
          <div class="modal-header">
            <div>
              <span class="eyebrow">ESPACE ETUDIANT</span>
              <h2>{{ examRecordTitle(selectedStudentExam) }}</h2>
            </div>
            <button class="icon-button" type="button" aria-label="Fermer" @click="closeStudentExam">
              <X :size="18" />
            </button>
          </div>

          <form class="student-exam-form" @submit.prevent="submitStudentExam">
            <article v-for="(question, index) in examQuestions(selectedStudentExam)" :key="question.numero || index" class="student-question">
              <div class="question-head">
                <strong>Question {{ question.numero || index + 1 }}</strong>
                <span class="status-pill">{{ question.points || question.bareme || 0 }} pts</span>
              </div>
              <p>{{ questionText(question) }}</p>

              <div v-if="questionChoices(question).length" class="student-choice-list">
                <label v-for="(choice, choiceIndex) in questionChoices(question)" :key="choice">
                  <input
                    v-model="studentAnswers[question.numero || index]"
                    type="radio"
                    :name="`question-${question.numero || index}`"
                    :value="choice"
                  />
                  <span class="choice-letter">{{ String.fromCharCode(65 + choiceIndex) }}</span>
                  <span>{{ choice }}</span>
                </label>
              </div>

              <textarea
                v-else
                v-model="studentAnswers[question.numero || index]"
                class="input-control"
                rows="3"
                placeholder="Ecris ta reponse..."
              />
            </article>

            <p v-if="studentExamMessage" class="helper-text">{{ studentExamMessage }}</p>

            <div class="draft-actions">
              <button class="btn btn-secondary" type="button" @click="closeStudentExam">Fermer</button>
              <button class="btn btn-success" type="submit">
                <Save :size="18" />
                <span>Soumettre les reponses</span>
              </button>
            </div>
          </form>
        </section>
      </div>

      <section v-if="activePage === 'dashboard'" class="dashboard-page">
        <div class="metric-grid">
          <article v-for="card in dashboardCards" :key="card.label" class="metric-card" :class="card.tone">
            <span>{{ card.label }}</span>
            <strong>{{ card.value }}</strong>
          </article>
        </div>

        <div class="dashboard-grid">
          <section class="panel">
            <div class="section-title">
              <BookOpenCheck :size="19" />
              <h2>Dernier workflow</h2>
            </div>
            <div v-if="workflowRun" class="real-summary">
              <strong>{{ workflowRun.status }}</strong>
              <span>{{ workflowRun.run_id }}</span>
            </div>
            <div v-else class="empty-state">
              Aucun workflow lance pour le moment.
            </div>
          </section>

          <section class="panel">
            <div class="section-title">
              <CalendarDays :size="19" />
              <h2>Agenda proche</h2>
            </div>
            <ul v-if="latestAgendaItems.length" class="activity-list">
              <li v-for="item in latestAgendaItems" :key="item.id">
                <strong>{{ formatDateTime(item.scheduled_at) }}</strong>
                <span>{{ item.title }} - {{ item.target_study_level }}</span>
              </li>
            </ul>
            <div v-else class="empty-state">Aucun evenement agenda enregistre.</div>
          </section>
        </div>
      </section>

      <section v-else-if="activePage === 'teacher-exams'" class="panel">
        <div class="section-title">
          <BookOpenCheck :size="19" />
          <h2>Mes examens</h2>
          <span class="status-pill">Gestion enseignant</span>
        </div>

        <div v-if="!publishedExams.length" class="empty-state">
          Aucun examen sauvegarde pour le moment.
        </div>

        <div v-else class="published-exam-list">
          <article
            v-for="exam in publishedExams"
            :key="exam.id"
            class="published-exam-card clickable-card"
            role="button"
            tabindex="0"
            @click="openTeacherExam(exam)"
            @keydown.enter="openTeacherExam(exam)"
          >
            <div>
              <strong>{{ examRecordTitle(exam) }}</strong>
              <span>{{ exam.evaluation_type }} - {{ exam.target_study_level }}</span>
              <small>{{ examQuestions(exam).length }} questions - {{ formatDateTime(exam.created_at) }}</small>
            </div>
            <span class="status-pill" :class="{ success: exam.status === 'published' }">
              {{ exam.status === "published" ? "Visible" : "Cache" }}
            </span>
          </article>
        </div>
      </section>

      <section v-else-if="activePage === 'student-exams'" class="panel">
        <div class="section-title">
          <BookOpenCheck :size="19" />
          <h2>Mes examens</h2>
          <span class="status-pill">{{ displayStudyLevel || "Etudiant" }}</span>
        </div>
        <div v-if="!studentPublishedExams.length" class="empty-state">
          Aucun examen publie pour ton niveau pour le moment.
        </div>
        <div v-else class="published-exam-list">
          <article
            v-for="exam in studentPublishedExams"
            :key="exam.id"
            class="published-exam-card clickable-card"
            role="button"
            tabindex="0"
            @click="openStudentExam(exam)"
            @keydown.enter="openStudentExam(exam)"
          >
            <div>
              <strong>{{ exam.title }}</strong>
              <span>{{ exam.evaluation_type }} - {{ exam.target_study_level }}</span>
              <small>{{ formatDateTime(exam.created_at) }}</small>
            </div>
            <span class="status-pill success">
              <PlayCircle :size="14" />
              Commencer
            </span>
          </article>
        </div>
      </section>

      <section v-else-if="activePage === 'student-notes'" class="panel">
        <div class="section-title">
          <NotebookPen :size="19" />
          <h2>Notes</h2>
          <span class="status-pill">Resultats</span>
        </div>
        <div class="empty-state">
          Aucune note publiee pour le moment.
        </div>
      </section>

      <section v-else-if="activePage === 'create-exam'" class="panel">
        <div class="section-title">
          <Sparkles :size="19" />
          <h2>Formulaire de generation d'examen</h2>
          <span class="status-pill">Agentic RAG</span>
        </div>

        <div class="embedded-kb-grid">
          <section>
            <div class="mini-section-title">
              <Library :size="18" />
              <strong>Ajouter les supports PDF</strong>
            </div>
            <KnowledgeBaseUploader :access-token="session.access_token" @created="handleKnowledgeBaseCreated" />
          </section>

          <section>
            <div class="mini-section-title">
              <Library :size="18" />
              <strong>Choisir la base a envoyer</strong>
            </div>
            <label class="field-label" for="kb-select">Knowledge base utilisee par le workflow</label>
            <select id="kb-select" v-model="selectedKnowledgeBaseId" class="input-control">
              <option value="" disabled>Importer ou choisir une base</option>
              <option v-for="kb in knowledgeBases" :key="kb.id" :value="kb.id">
                {{ kb.name }} - {{ kb.documents.length }} document(s)
              </option>
            </select>
            <p v-if="selectedKnowledgeBase" class="helper-text">
              Le workflow recevra l'ID de session RAG et les chunks pertinents selectionnes.
            </p>
            <p v-else class="helper-text">
              Aucune base selectionnee. Importe un PDF avant de generer l'examen.
            </p>
          </section>
        </div>

        <ExamGenerationForm
          :disabled="isGenerating"
          :is-generating="isGenerating"
          @submit="handleGenerate"
        />

        <p v-if="generationMessage" class="helper-text generation-message">
          {{ generationMessage }}
        </p>

        <ExamDraftPreview
          v-if="draftExam"
          :exam="draftExam"
          :is-publishing="isPublishingExam"
          :publish-message="publishMessage"
          @regenerate="handleRegenerateExam"
          @publish="handlePublishGeneratedExam"
        />
      </section>

      <section v-else-if="activePage === 'agenda'" class="panel">
        <div class="section-title">
          <CalendarDays :size="19" />
          <h2>Agenda</h2>
          <span class="status-pill">{{ isStudent ? displayStudyLevel || "Etudiant" : "Planification" }}</span>
        </div>

        <form v-if="canManagePedagogy" class="agenda-form" @submit.prevent="handleCreateAgendaItem">
          <label>
            <span class="field-label">Titre</span>
            <input v-model="agendaForm.title" class="input-control" placeholder="Ex. Controle de droit des contrats" />
          </label>
          <label>
            <span class="field-label">Classe / niveau visible</span>
            <select v-model="agendaForm.target_study_level" class="input-control">
              <option v-for="level in studyLevels" :key="level">{{ level }}</option>
            </select>
          </label>
          <label>
            <span class="field-label">Type</span>
            <select v-model="agendaForm.evaluation_type" class="input-control">
              <option>Controle continu</option>
              <option>Examen final</option>
              <option>Quiz</option>
              <option>TP</option>
              <option>Rattrapage</option>
            </select>
          </label>
          <label>
            <span class="field-label">Date</span>
            <input v-model="agendaForm.scheduled_at" class="input-control" type="datetime-local" />
          </label>
          <label class="span-2">
            <span class="field-label">Description</span>
            <textarea v-model="agendaForm.description" class="input-control" rows="3" />
          </label>
          <button class="btn btn-primary" type="submit" :disabled="isSavingAgenda">
            <CalendarDays :size="18" />
            <span>{{ isSavingAgenda ? "Ajout..." : "Ajouter a l'agenda" }}</span>
          </button>
        </form>

        <p v-if="agendaMessage" class="helper-text">{{ agendaMessage }}</p>

        <div v-if="agendaItems.length" class="agenda-list">
          <article v-for="item in agendaItems" :key="item.id">
            <div>
              <strong>{{ formatDateTime(item.scheduled_at) }}</strong>
              <span>{{ item.title }}</span>
              <small v-if="item.description">{{ item.description }}</small>
            </div>
            <span class="status-pill">{{ item.target_study_level }}</span>
          </article>
        </div>
        <div v-else class="empty-state">
          {{
            isStudent
              ? `Aucun evenement pour ton niveau (${displayStudyLevel || "niveau non defini"}).`
              : "Aucun evenement cree. Ajoute le premier evenement pour une classe."
          }}
        </div>
      </section>

      <section v-else-if="activePage === 'administration'" class="panel">
        <div class="section-title">
          <UsersRound :size="19" />
          <h2>Administration</h2>
          <button class="btn btn-primary" type="button" @click="showAdminModal = true">
            <UserPlus :size="18" />
            <span>Creer compte</span>
          </button>
        </div>

        <p v-if="adminMessage" class="helper-text">{{ adminMessage }}</p>

        <div class="table-toolbar">
          <strong>Profils utilisateurs</strong>
          <button class="btn btn-secondary" type="button" :disabled="isLoadingProfiles" @click="refreshAdminProfiles">
            <UsersRound :size="18" />
            <span>{{ isLoadingProfiles ? "Chargement..." : "Actualiser" }}</span>
          </button>
        </div>

        <div class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Role</th>
                <th>Niveau</th>
                <th>ID</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!adminProfiles.length">
                <td colspan="5">Aucun profil trouve.</td>
              </tr>
              <tr v-for="row in adminProfiles" :key="row.id">
                <td>
                  <input v-model="row.full_name" class="table-input" placeholder="Nom complet" />
                </td>
                <td>
                  <select v-model="row.role" class="table-input">
                    <option value="student">student</option>
                    <option value="teacher">teacher</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td>
                  <select v-if="row.role === 'student'" v-model="row.study_level" class="table-input">
                    <option value="">Non defini</option>
                    <option v-for="level in studyLevels" :key="level">{{ level }}</option>
                  </select>
                  <span v-else class="muted-cell">-</span>
                </td>
                <td>
                  <code>{{ row.id }}</code>
                </td>
                <td>
                  <div class="table-actions">
                    <button class="icon-button" type="button" aria-label="Sauvegarder" @click="handleSaveProfile(row)">
                      <Save :size="16" />
                    </button>
                    <button class="icon-button danger" type="button" aria-label="Supprimer" @click="handleDeleteProfile(row)">
                      <Trash2 :size="16" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-else class="results-grid single-result">
        <WorkflowResult v-if="workflowRun" :run="workflowRun" />
        <section v-else class="panel">
          <div class="section-title">
            <FileText :size="19" />
            <h2>Aucun workflow lance</h2>
          </div>
          <p class="helper-text">Lance une generation depuis l'onglet Creer examen pour voir la reponse webhook.</p>
        </section>
      </section>
    </section>
  </main>
</template>
