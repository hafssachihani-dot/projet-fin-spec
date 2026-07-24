<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  BarChart3,
  Activity,
  BookOpenCheck,
  CalendarDays,
  Eye,
  EyeOff,
  FileText,
  Library,
  NotebookPen,
  Pencil,
  PlayCircle,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserPlus,
  UsersRound,
  X,
} from "lucide-vue-next";
import AuthPanel from "./components/AuthPanel.vue";
import PublicLanding from "./components/PublicLanding.vue";
import AdminStudentManager from "./components/AdminStudentManager.vue";
import AgendaCalendar from "./components/AgendaCalendar.vue";
import AgentObservabilityDashboard from "./components/AgentObservabilityDashboard.vue";
import AppSidebar from "./components/AppSidebar.vue";
import AppTopbar from "./components/AppTopbar.vue";
import KnowledgeBaseUploader from "./components/KnowledgeBaseUploader.vue";
import ExamGenerationForm from "./components/ExamGenerationForm.vue";
import ExamDraftPreview from "./components/ExamDraftPreview.vue";
import WorkflowResult from "./components/WorkflowResult.vue";
import {
  clearLatestWorkflowResult,
  createAgenda,
  deleteClassResource,
  deletePublishedExam,
  deleteProfile,
  generateExam,
  getLatestWorkflowResult,
  getAgentTelemetryDashboard,
  getStaffDashboard,
  fetchClassResourceBlob,
  listAgenda,
  listClassResources,
  listKnowledgeBases,
  launchPedagogicalReport,
  listPublishedExams,
  listProfiles,
  listStaffResults,
  listStudentAttempts,
  publishGeneratedExam,
  reviewExamApproval,
  submitStudentAttempt,
  uploadClassResource,
  updateProfile,
  updatePublishedExam,
  updatePublishedExamVisibility,
} from "./services/api";
import {
  getCurrentProfile,
  refreshCurrentSession,
  signOut,
} from "./services/supabase";

const knowledgeBases = ref([]);
const selectedKnowledgeBaseId = ref("");
const knowledgeBaseUploader = ref(null);
const workflowRun = ref(null);
const draftExam = ref(null);
const lastExamForm = ref(null);
const publishedExams = ref([]);
const isGenerating = ref(false);
const isPublishingExam = ref(false);
const isReviewingExamApproval = ref(false);
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
const isEditingTeacherExam = ref(false);
const editableTeacherExam = ref(null);
const selectedStudentExam = ref(null);
const selectedGradeAttempt = ref(null);
const studentAttempts = ref([]);
const studentAnswers = ref({});
const studentExamMessage = ref("");
const isSubmittingStudentExam = ref(false);
const studentExamSubmitted = ref(false);
const staffResults = ref([]);
const staffResultsStudyLevel = ref("");
const isLoadingStaffResults = ref(false);
const dashboardMetrics = ref(null);
const dashboardStudyLevel = ref("Licence 2");
const dashboardAcademicYear = ref("");
const isLoadingDashboard = ref(false);
const agentTelemetryDashboard = ref(null);
const agentTelemetryPeriod = ref(30);
const isLoadingAgentTelemetry = ref(false);
const isRefreshingPage = ref(false);
const pedagogicalReportRun = ref(null);
const pedagogicalReportResult = ref(null);
const pedagogicalReportMessage = ref("");
const isLaunchingPedagogicalReport = ref(false);
const classResources = ref([]);
const selectedClassResource = ref(null);
const resourcePreviewUrl = ref("");
const resourceFile = ref(null);
const resourceFileInput = ref(null);
const resourceMessage = ref("");
const isLoadingResources = ref(false);
const isUploadingResource = ref(false);
const isLoadingResourcePreview = ref(false);

const authLoading = ref(true);
const session = ref(null);
const profile = ref(null);
const showLogin = ref(false);
const showAdminModal = ref(false);

const studyLevels = ["Licence 1", "Licence 2", "Licence 3", "Master 1", "Master 2"];

const agendaForm = reactive({
  title: "",
  target_study_level: "Licence 2",
  evaluation_type: "Controle continu",
  scheduled_at: "",
  description: "",
});

const resourceForm = reactive({
  title: "",
  description: "",
  target_study_level: "Licence 2",
});

const today = new Date();
const academicYearStart = today.getMonth() >= 8
  ? today.getFullYear()
  : today.getFullYear() - 1;
const pedagogicalReportForm = reactive({
  analysis_type: "student_analysis",
  study_level: "Licence 2",
  academic_year: `${academicYearStart}-${academicYearStart + 1}`,
});
dashboardAcademicYear.value = pedagogicalReportForm.academic_year;

const displayRole = computed(() =>
  String(profile.value?.role || session.value?.user?.user_metadata?.role || "unknown")
    .trim()
    .toLowerCase()
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
const selectedResourceIsImage = computed(() =>
  String(selectedClassResource.value?.content_type || "").startsWith("image/")
);

const gradedStudentAttempts = computed(() =>
  studentAttempts.value.filter((attempt) => attempt.status === "graded")
);

const navigationItems = computed(() => {
  if (isStudent.value) {
    return [
      { key: "student-exams", label: "Mes examens", icon: BookOpenCheck },
      { key: "student-notes", label: "Notes", icon: NotebookPen },
      { key: "resources", label: "Ressources", icon: Library },
      { key: "agenda", label: "Agenda", icon: CalendarDays },
    ];
  }

  const items = [{ key: "dashboard", label: "Dashboard", icon: BarChart3 }];

  if (isAdmin.value) {
    items.push({ key: "exam-approvals", label: "Validations examens", icon: ShieldCheck });
    items.push({ key: "pedagogical-analysis", label: "Analyse pedagogique", icon: BarChart3 });
    items.push({ key: "agent-observability", label: "Observabilite agents", icon: Activity });
  }

  if (canManagePedagogy.value) {
    items.push({ key: "create-exam", label: "Creer examen", icon: Sparkles });
    items.push({ key: "teacher-exams", label: "Mes examens", icon: BookOpenCheck });
    items.push({ key: "staff-results", label: "Resultats", icon: NotebookPen });
    items.push({ key: "resources", label: "Ressources", icon: Library });
  }

  items.push({ key: "agenda", label: "Agenda", icon: CalendarDays });

  if (isAdmin.value) {
    items.push({ key: "administration", label: "Administration", icon: UsersRound });
  }

  return items;
});

const dashboardCards = computed(() => {
  if (isStudent.value) {
    return [
      { label: "Examens disponibles", value: studentPublishedExams.value.length, tone: "cyan" },
      { label: "Evenements agenda", value: agendaItems.value.length, tone: "purple" },
      { label: "Notes publiees", value: gradedStudentAttempts.value.length, tone: "green" },
      { label: "Niveau", value: displayStudyLevel.value || "-", tone: "mint" },
    ];
  }

  const summary = dashboardMetrics.value?.summary || {};
  return [
    { label: "Etudiants", value: summary.student_count ?? 0, tone: "cyan" },
    { label: "Examens publies", value: summary.exam_count ?? 0, tone: "purple" },
    { label: "Moyenne de classe", value: `${summary.class_average_percent ?? 0} %`, tone: "green" },
    { label: "Participation", value: `${summary.participation_percent ?? 0} %`, tone: "mint" },
  ];
});

const pageTitle = computed(() => {
  const labels = {
    dashboard: "Dashboard",
    "student-exams": "Mes examens",
    "student-notes": "Notes",
    "create-exam": "Creer examen",
    "teacher-exams": "Mes examens",
    "exam-approvals": "Validations examens",
    "staff-results": "Resultats",
    resources: "Ressources de classe",
    agenda: "Agenda",
    administration: "Administration",
    "pedagogical-analysis": "Analyse pedagogique",
    "agent-observability": "Observabilite des agents",
  };
  return labels[activePage.value] || "Dashboard";
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

const adminApprovalExams = computed(() =>
  publishedExams.value.filter((record) => Boolean((record.exam || {})._approval))
);

function examApproval(record) {
  return (record?.exam || {})._approval || {};
}

function examApprovalStatus(record) {
  return examApproval(record).status || (record?.status === "published" ? "approved" : "legacy");
}

function examApprovalLabel(record) {
  const labels = {
    pending: "En attente administration",
    approved: record?.status === "published" ? "Publie aux etudiants" : "Accepte par l'administration",
    rejected: "Refuse par administration",
    legacy: record?.status === "published" ? "Visible" : "Cache",
  };
  return labels[examApprovalStatus(record)] || "En attente";
}

const studentAttemptsByExamId = computed(() => {
  const attempts = {};
  for (const attempt of studentAttempts.value) {
    attempts[attempt.exam_id] = attempt;
  }
  return attempts;
});

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

function normalizeStudyLevel(value) {
  return String(value || "").trim().toLocaleLowerCase("fr");
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

function ensureEditableQuestion(question, index) {
  return {
    numero: question.numero || index + 1,
    type: question.type || "",
    enonce: questionText(question),
    choix: questionChoices(question),
    bonne_reponse: question.bonne_reponse || question.correct_answer || question.reponse_correcte || "",
    reponse_attendue: question.reponse_attendue || question.expected_answer || "",
    points: question.points ?? question.bareme ?? 0,
  };
}

function buildEditableExam(record) {
  const exam = structuredClone(examRecordPayload(record));
  exam.module = exam.module || record.title || "Examen";
  exam.niveau = exam.niveau || exam.study_level || record.target_study_level || "";
  exam.type_evaluation = exam.type_evaluation || exam.evaluation_type || record.evaluation_type || "";
  exam.questions = (exam.questions || []).map(ensureEditableQuestion);
  return exam;
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

async function waitForWorkflowCallback(delayMs = 2000) {
  const startedAt = Date.now();

  while (true) {
    const elapsedSeconds = Math.floor((Date.now() - startedAt) / 1000);
    generationMessage.value = `Workflow lance. Attente des questions (${elapsedSeconds} s)...`;
    const latestResult = await getLatestWorkflowResult();
    const exam = extractGeneratedExam(latestResult);
    if (exam) {
      return exam;
    }
    await wait(delayMs);
  }
}

function findPedagogicalReport(value, visited = new Set()) {
  const unwrappedValue = unwrapWorkflowPayload(value);

  if (!unwrappedValue || typeof unwrappedValue !== "object") return null;
  if (visited.has(unwrappedValue)) return null;
  visited.add(unwrappedValue);

  if (Array.isArray(unwrappedValue)) {
    for (const item of unwrappedValue) {
      const found = findPedagogicalReport(item, visited);
      if (found) return found;
    }
    return null;
  }

  const isExamAudit =
    "score_sur_100" in unwrappedValue &&
    ("decision" in unwrappedValue || "resume" in unwrappedValue);
  const isStudentAnalysis =
    "analysis_type" in unwrappedValue &&
    ("summary" in unwrappedValue || "resume" in unwrappedValue || "recommendations" in unwrappedValue);

  if (isExamAudit || isStudentAnalysis) return unwrappedValue;

  for (const item of Object.values(unwrappedValue)) {
    const found = findPedagogicalReport(item, visited);
    if (found) return found;
  }
  return null;
}

function extractPedagogicalResponse(value) {
  const report = findPedagogicalReport(value);
  if (report) return report;

  // Some agents return a final plain-text report inside { text: "..." }.
  // It is still a completed callback and must stop the polling immediately.
  const unwrappedValue = unwrapWorkflowPayload(value);
  if (typeof unwrappedValue === "string" && unwrappedValue.trim()) {
    return {
      analysis_type: "student_analysis",
      status: "COMPLETED",
      summary: unwrappedValue.trim(),
    };
  }

  return null;
}

async function waitForPedagogicalReport(maxAttempts = 60, delayMs = 3000) {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    pedagogicalReportMessage.value = "Workflow en cours. Attente du rapport final...";
    const latestResult = await getLatestWorkflowResult();
    const report = extractPedagogicalResponse(latestResult);
    if (report) return report;
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
    if (/session_not_found|invalid refresh token|bad_jwt/i.test(error.message || "")) {
      await signOut().catch(() => {});
      session.value = null;
      profile.value = null;
    }
    errorMessage.value = error.message;
  }
}

async function refreshStudentAttempts() {
  try {
    if (!isStudent.value || !session.value?.access_token) {
      studentAttempts.value = [];
      return;
    }
    studentAttempts.value = await listStudentAttempts(session.value.access_token);
  } catch (error) {
    studentAttempts.value = [];
    errorMessage.value = error.message;
  }
}

async function refreshStaffResults() {
  if (!canManagePedagogy.value || !session.value?.access_token) {
    staffResults.value = [];
    return;
  }

  isLoadingStaffResults.value = true;
  try {
    staffResults.value = await listStaffResults(
      session.value.access_token,
      staffResultsStudyLevel.value
    );
  } catch (error) {
    staffResults.value = [];
    errorMessage.value = error.message;
  } finally {
    isLoadingStaffResults.value = false;
  }
}

async function refreshDashboardMetrics() {
  if (!canManagePedagogy.value || !session.value?.access_token) {
    dashboardMetrics.value = null;
    return;
  }

  isLoadingDashboard.value = true;
  try {
    dashboardMetrics.value = await getStaffDashboard(
      session.value.access_token,
      dashboardStudyLevel.value,
      dashboardAcademicYear.value
    );
  } catch (error) {
    dashboardMetrics.value = null;
    errorMessage.value = error.message;
  } finally {
    isLoadingDashboard.value = false;
  }
}

async function refreshAgentTelemetryDashboard() {
  if (!isAdmin.value || !session.value?.access_token) {
    agentTelemetryDashboard.value = null;
    return;
  }

  isLoadingAgentTelemetry.value = true;
  try {
    agentTelemetryDashboard.value = await getAgentTelemetryDashboard(
      session.value.access_token,
      agentTelemetryPeriod.value
    );
  } catch (error) {
    agentTelemetryDashboard.value = null;
    errorMessage.value = error.message;
  } finally {
    isLoadingAgentTelemetry.value = false;
  }
}

function updateAgentTelemetryPeriod(value) {
  agentTelemetryPeriod.value = value;
  refreshAgentTelemetryDashboard();
}

async function refreshClassResources() {
  if (!session.value?.access_token) {
    classResources.value = [];
    return;
  }

  isLoadingResources.value = true;
  resourceMessage.value = "";
  try {
    classResources.value = await listClassResources(session.value.access_token);
  } catch (error) {
    classResources.value = [];
    resourceMessage.value = error.message;
  } finally {
    isLoadingResources.value = false;
  }
}

function handleSidebarNavigate(page) {
  activePage.value = page;
  if (page === "dashboard") {
    refreshDashboardMetrics();
  }
  if (page === "teacher-exams" || page === "student-exams" || page === "student-notes") {
    refreshPublishedExams();
    refreshStudentAttempts();
  }
  if (page === "staff-results") {
    refreshStaffResults();
  }
  if (page === "pedagogical-analysis") {
    refreshPublishedExams();
  }
  if (page === "agent-observability") {
    refreshAgentTelemetryDashboard();
  }
  if (page === "resources") {
    refreshClassResources();
  }
}

async function refreshActivePage() {
  if (isRefreshingPage.value) return;

  isRefreshingPage.value = true;
  errorMessage.value = "";
  try {
    switch (activePage.value) {
      case "dashboard":
        await Promise.all([refreshDashboardMetrics(), refreshPublishedExams(), refreshStudentAttempts()]);
        break;
      case "teacher-exams":
      case "exam-approvals":
      case "student-exams":
      case "student-notes":
        await Promise.all([refreshPublishedExams(), refreshStudentAttempts()]);
        break;
      case "staff-results":
        await refreshStaffResults();
        break;
      case "agenda":
        await refreshAgendaItems();
        break;
      case "resources":
        await refreshClassResources();
        break;
      case "create-exam":
        await refreshKnowledgeBases();
        break;
      case "administration":
        await refreshAdminProfiles();
        break;
      case "agent-observability":
        await refreshAgentTelemetryDashboard();
        break;
      case "pedagogical-analysis": {
        const latestResult = await getLatestWorkflowResult();
        const report = extractPedagogicalResponse(latestResult);
        if (report) pedagogicalReportResult.value = report;
        break;
      }
      default:
        await Promise.all([refreshPublishedExams(), refreshAgendaItems()]);
    }
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isRefreshingPage.value = false;
  }
}

function handleResourceFile(event) {
  resourceFile.value = event.target.files?.[0] || null;
  if (resourceFile.value && !resourceForm.title) {
    resourceForm.title = resourceFile.value.name.replace(/\.[^.]+$/, "");
  }
}

function formatFileSize(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

async function handleUploadClassResource() {
  resourceMessage.value = "";
  if (!resourceForm.title.trim() || !resourceForm.target_study_level || !resourceFile.value) {
    resourceMessage.value = "Ajoute un titre, une classe et un fichier PDF ou image.";
    return;
  }

  isUploadingResource.value = true;
  try {
    await uploadClassResource(session.value.access_token, {
      title: resourceForm.title,
      description: resourceForm.description,
      targetStudyLevel: resourceForm.target_study_level,
      file: resourceFile.value,
    });
    resourceForm.title = "";
    resourceForm.description = "";
    resourceFile.value = null;
    if (resourceFileInput.value) resourceFileInput.value.value = "";
    await refreshClassResources();
    resourceMessage.value = "Ressource publiee pour la classe selectionnee.";
  } catch (error) {
    resourceMessage.value = error.message;
  } finally {
    isUploadingResource.value = false;
  }
}

async function openClassResource(resource) {
  closeClassResource();
  selectedClassResource.value = resource;
  isLoadingResourcePreview.value = true;
  resourceMessage.value = "";
  try {
    const blob = await fetchClassResourceBlob(session.value.access_token, resource.id);
    resourcePreviewUrl.value = URL.createObjectURL(blob);
  } catch (error) {
    resourceMessage.value = error.message;
  } finally {
    isLoadingResourcePreview.value = false;
  }
}

function closeClassResource() {
  if (resourcePreviewUrl.value) URL.revokeObjectURL(resourcePreviewUrl.value);
  resourcePreviewUrl.value = "";
  selectedClassResource.value = null;
  isLoadingResourcePreview.value = false;
}

async function handleDeleteClassResource(resource) {
  if (!window.confirm(`Supprimer la ressource "${resource.title}" ?`)) return;
  try {
    await deleteClassResource(session.value.access_token, resource.id);
    closeClassResource();
    await refreshClassResources();
    resourceMessage.value = "Ressource supprimee.";
  } catch (error) {
    resourceMessage.value = error.message;
  }
}

async function handleLaunchPedagogicalReport() {
  pedagogicalReportMessage.value = "";
  pedagogicalReportRun.value = null;
  pedagogicalReportResult.value = null;

  isLaunchingPedagogicalReport.value = true;
  try {
    const refreshedSession = await refreshCurrentSession();
    if (!refreshedSession?.access_token) {
      throw new Error("Session expiree. Reconnecte-toi avant de lancer l'analyse.");
    }
    session.value = refreshedSession;
    await clearLatestWorkflowResult();
    pedagogicalReportRun.value = await launchPedagogicalReport(refreshedSession.access_token, {
      analysis_type: "student_analysis",
      study_level: pedagogicalReportForm.study_level,
      academic_year: pedagogicalReportForm.academic_year,
      exam_id: null,
    });
    pedagogicalReportResult.value = await waitForPedagogicalReport();
    pedagogicalReportMessage.value = pedagogicalReportResult.value
      ? "Rapport pedagogique recu."
      : "Le workflow est lance, mais aucun rapport final n'a ete recu. Verifie l'API Request finale vers /api/workflow/callback.";
  } catch (error) {
    if (error.code === "AUTH_SESSION_EXPIRED" || /session_not_found|invalid refresh token|bad_jwt/i.test(error.message || "")) {
      session.value = null;
      profile.value = null;
    }
    pedagogicalReportMessage.value = error.message;
  } finally {
    isLaunchingPedagogicalReport.value = false;
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
  await refreshStudentAttempts();
  await refreshAdminProfiles();
  await refreshDashboardMetrics();
  await refreshClassResources();
  if (isStudent.value && activePage.value === "dashboard") {
    activePage.value = "student-exams";
  }
}

async function handleAuthenticated(activeSession) {
  errorMessage.value = "";
  try {
    await loadAuthenticatedUser(activeSession);
    showLogin.value = false;
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function handleSignOut() {
  await signOut();
  session.value = null;
  profile.value = null;
  showLogin.value = false;
  knowledgeBases.value = [];
  agendaItems.value = [];
  adminProfiles.value = [];
  publishedExams.value = [];
  studentAttempts.value = [];
  classResources.value = [];
  closeClassResource();
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

  isGenerating.value = true;
  try {
    let knowledgeBaseId = selectedKnowledgeBaseId.value;
    const hasNewFiles = knowledgeBaseUploader.value?.hasSelectedFiles?.() ?? false;

    if (hasNewFiles) {
      generationMessage.value = "Creation de la base documentaire...";
      const knowledgeBase = await knowledgeBaseUploader.value.createFromSelectedFiles();
      knowledgeBaseId = knowledgeBase.id;
    }

    if (!knowledgeBaseId) {
      throw new Error("Importe au moins un PDF avant de generer l'examen.");
    }

    selectedKnowledgeBaseId.value = knowledgeBaseId;
    lastExamForm.value = {
      ...form,
      knowledge_base_id: knowledgeBaseId,
    };
    workflowRun.value = {
      status: "running",
      knowledge_base_id: knowledgeBaseId,
    };
    generationMessage.value = "Base prete. Lancement du workflow...";
    await clearLatestWorkflowResult();
    workflowRun.value = await generateExam({
      ...form,
      knowledge_base_id: knowledgeBaseId,
    });
    draftExam.value = extractGeneratedExam(workflowRun.value.workflow_response);
    if (!draftExam.value) {
      isWaitingForCallback.value = true;
      draftExam.value = await waitForWorkflowCallback();
    }
    if (draftExam.value) {
      // The workflow may omit this ID even though it received it as input.
      draftExam.value = {
        ...draftExam.value,
        knowledge_base_id: draftExam.value.knowledge_base_id || knowledgeBaseId,
      };
    }
    activePage.value = "create-exam";
    generationMessage.value = "Questions recues. L'enseignant peut verifier le brouillon.";
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
    const refreshedSession = await refreshCurrentSession();
    if (!refreshedSession?.access_token) {
      throw new Error("Session expiree. Reconnecte-toi puis recommence la publication.");
    }
    session.value = refreshedSession;

    const knowledgeBaseId =
      draftExam.value.knowledge_base_id ||
      lastExamForm.value?.knowledge_base_id ||
      selectedKnowledgeBaseId.value;
    const examToPublish = {
      ...draftExam.value,
      knowledge_base_id: knowledgeBaseId,
    };

    await publishGeneratedExam(refreshedSession.access_token, {
      exam: examToPublish,
      knowledge_base_id: knowledgeBaseId,
      target_study_level: draftExam.value.niveau || draftExam.value.study_level || lastExamForm.value?.study_level || "Licence 2",
      teacher_note: "Examen valide par l'enseignant.",
    });
    draftExam.value = null;
    generationMessage.value = "Examen transmis a l'administration pour verification.";
    await refreshPublishedExams();
    publishMessage.value = "";
  } catch (error) {
    if (error.code === "AUTH_SESSION_EXPIRED") {
      session.value = null;
      profile.value = null;
    }
    errorMessage.value = error.message;
  } finally {
    isPublishingExam.value = false;
  }
}

function handleEditPublishedExam(record) {
  editableTeacherExam.value = buildEditableExam(record);
  isEditingTeacherExam.value = true;
}

function cancelTeacherExamEdit() {
  editableTeacherExam.value = null;
  isEditingTeacherExam.value = false;
}

async function saveTeacherExamEdit() {
  if (!session.value?.access_token || !selectedTeacherExam.value || !editableTeacherExam.value) return;

  try {
    const updated = await updatePublishedExam(session.value.access_token, selectedTeacherExam.value.id, {
      exam: editableTeacherExam.value,
      target_study_level: editableTeacherExam.value.niveau || selectedTeacherExam.value.target_study_level,
      teacher_note: selectedTeacherExam.value.teacher_note || "",
    });
    publishedExams.value = publishedExams.value.map((item) => (item.id === updated.id ? updated : item));
    selectedTeacherExam.value = updated;
    cancelTeacherExamEdit();
  } catch (error) {
    errorMessage.value = error.message;
  }
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

async function handleReviewExamApproval(record, decision) {
  if (!isAdmin.value || !session.value?.access_token || isReviewingExamApproval.value) return;
  let reason = "";
  if (decision === "reject") {
    reason = window.prompt("Motif du refus (visible par l'enseignant) :", "") || "";
    if (!reason.trim()) return;
  }

  isReviewingExamApproval.value = true;
  errorMessage.value = "";
  try {
    const updated = await reviewExamApproval(session.value.access_token, record.id, decision, reason);
    publishedExams.value = publishedExams.value.map((item) => (item.id === updated.id ? updated : item));
    selectedTeacherExam.value = updated;
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isReviewingExamApproval.value = false;
  }
}

function openTeacherExam(record) {
  selectedTeacherExam.value = record;
}

function closeTeacherExam() {
  selectedTeacherExam.value = null;
  cancelTeacherExamEdit();
}

function openStudentExam(record) {
  selectedStudentExam.value = record;
  const attempt = studentAttemptsByExamId.value[record.id];
  studentExamSubmitted.value = Boolean(attempt);
  studentAnswers.value = {};

  if (attempt?.answers?.length) {
    for (const answer of attempt.answers) {
      studentAnswers.value[answer.question_number] = answer.student_answer || "";
    }
  }

  if (attempt) {
    studentExamMessage.value = `Examen deja soumis. correlation_id: ${attempt.correlation_id || attempt.id}.`;
  } else {
    studentExamMessage.value = "";
  }
}

function closeStudentExam() {
  selectedStudentExam.value = null;
  studentAnswers.value = {};
  studentExamMessage.value = "";
  studentExamSubmitted.value = false;
}

function openGradeDetails(attempt) {
  selectedGradeAttempt.value = attempt;
}

function closeGradeDetails() {
  selectedGradeAttempt.value = null;
}

async function submitStudentExam() {
  if (!session.value?.access_token || !selectedStudentExam.value) return;

  const answers = examQuestions(selectedStudentExam.value).map((question, index) => {
    const questionNumber = Number(question.numero || question.number || index + 1);
    return {
      question_number: questionNumber,
      answer: studentAnswers.value[questionNumber] || "",
    };
  });

  const missingAnswer = answers.find((answer) => !String(answer.answer).trim());
  if (missingAnswer) {
    studentExamMessage.value = `Reponds a la question ${missingAnswer.question_number} avant de soumettre.`;
    return;
  }

  isSubmittingStudentExam.value = true;
  studentExamMessage.value = "Enregistrement des reponses...";
  try {
    const result = await submitStudentAttempt(session.value.access_token, {
      exam_id: selectedStudentExam.value.id,
      answers,
    });
    if (result.workflow_status === "launched") {
      studentExamMessage.value = `Reponses sauvegardees. Workflow etudiant lance. correlation_id: ${result.correlation_id}.`;
    } else if (result.workflow_status === "launch_failed") {
      studentExamMessage.value = `Reponses sauvegardees, mais le workflow n'a pas demarre: ${result.workflow_error}`;
    } else {
      studentExamMessage.value = `Reponses sauvegardees. Ajoute A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL pour lancer le workflow. correlation_id: ${result.correlation_id}.`;
    }
    studentExamSubmitted.value = true;
    await refreshStudentAttempts();
  } catch (error) {
    studentExamMessage.value = error.message;
  } finally {
    isSubmittingStudentExam.value = false;
  }
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

function handleSessionExpired() {
  session.value = null;
  profile.value = null;
  showLogin.value = true;
  errorMessage.value = "Ta session a expire. Reconnecte-toi pour continuer.";
}

function handleSessionRefreshed(event) {
  if (event.detail?.access_token) session.value = event.detail;
}

onMounted(async () => {
  window.addEventListener("auth-session-expired", handleSessionExpired);
  window.addEventListener("auth-session-refreshed", handleSessionRefreshed);
  try {
    // A locally cached JWT can still look valid after its server session was revoked.
    const activeSession = await refreshCurrentSession();
    if (activeSession) {
      await loadAuthenticatedUser(activeSession);
    }
  } catch (error) {
    session.value = null;
    profile.value = null;
    errorMessage.value = error.message;
  } finally {
    authLoading.value = false;
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("auth-session-expired", handleSessionExpired);
  window.removeEventListener("auth-session-refreshed", handleSessionRefreshed);
});
</script>

<template>
  <PublicLanding
    v-if="!authLoading && !session && !showLogin"
    @login="showLogin = true"
  />

  <AuthPanel
    v-else-if="!authLoading && !session"
    @authenticated="handleAuthenticated"
    @back="showLogin = false"
  />

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
        :is-refreshing="isRefreshingPage"
        @create-user="showAdminModal = true"
        @refresh="refreshActivePage"
        @sign-out="handleSignOut"
      />

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <AdminStudentManager
        v-if="isAdmin && showAdminModal"
        :access-token="session.access_token"
        @close="handleAdminModalClose"
      />

      <div v-if="selectedClassResource" class="modal-backdrop" @click.self="closeClassResource">
        <section class="admin-modal resource-preview-modal">
          <div class="modal-header">
            <div>
              <span class="eyebrow">RESSOURCE DE CLASSE</span>
              <h2>{{ selectedClassResource.title }}</h2>
            </div>
            <button class="icon-button" type="button" aria-label="Fermer" @click="closeClassResource">
              <X :size="18" />
            </button>
          </div>

          <div class="resource-preview-meta">
            <span class="status-pill">{{ selectedClassResource.target_study_level }}</span>
            <span>{{ selectedClassResource.filename }}</span>
            <span>{{ formatFileSize(selectedClassResource.size_bytes) }}</span>
          </div>

          <div class="resource-preview-area">
            <div v-if="isLoadingResourcePreview" class="empty-state">Chargement du document...</div>
            <img
              v-else-if="resourcePreviewUrl && selectedResourceIsImage"
              :src="resourcePreviewUrl"
              :alt="selectedClassResource.title"
            />
            <iframe
              v-else-if="resourcePreviewUrl"
              :src="resourcePreviewUrl"
              :title="selectedClassResource.title"
            />
            <div v-else class="empty-state">Le fichier ne peut pas etre affiche.</div>
          </div>

          <div class="draft-actions">
            <a
              v-if="resourcePreviewUrl"
              class="btn btn-secondary"
              :href="resourcePreviewUrl"
              :download="selectedClassResource.filename"
            >Telecharger</a>
            <button
              v-if="canManagePedagogy"
              class="btn btn-danger"
              type="button"
              @click="handleDeleteClassResource(selectedClassResource)"
            >
              <Trash2 :size="18" />
              <span>Supprimer</span>
            </button>
            <button class="btn btn-secondary" type="button" @click="closeClassResource">Fermer</button>
          </div>
        </section>
      </div>

      <div v-if="selectedTeacherExam" class="modal-backdrop" @click.self="closeTeacherExam">
        <section class="admin-modal exam-manager-modal">
          <div class="modal-header">
            <div>
              <span class="eyebrow">{{ isAdmin ? "ADMINISTRATION" : "ENSEIGNANT" }}</span>
              <h2>{{ examRecordTitle(selectedTeacherExam) }}</h2>
            </div>
            <button class="icon-button" type="button" aria-label="Fermer" @click="closeTeacherExam">
              <X :size="18" />
            </button>
          </div>

          <div class="exam-detail-summary">
            <span class="status-pill" :class="{ success: examApprovalStatus(selectedTeacherExam) === 'approved' }">
              {{ examApprovalLabel(selectedTeacherExam) }}
            </span>
            <span>{{ selectedTeacherExam.evaluation_type }} - {{ selectedTeacherExam.target_study_level }}</span>
            <span>{{ examQuestions(selectedTeacherExam).length }} questions</span>
          </div>

          <div v-if="isEditingTeacherExam" class="exam-edit-form">
            <label>
              <span class="field-label">Module</span>
              <input v-model="editableTeacherExam.module" class="input-control" />
            </label>
            <label>
              <span class="field-label">Niveau</span>
              <select v-model="editableTeacherExam.niveau" class="input-control">
                <option v-for="level in studyLevels" :key="level">{{ level }}</option>
              </select>
            </label>
            <label class="span-2">
              <span class="field-label">Type d'evaluation</span>
              <input v-model="editableTeacherExam.type_evaluation" class="input-control" />
            </label>

            <article v-for="(question, index) in editableTeacherExam.questions" :key="question.numero || index" class="exam-edit-question">
              <div class="question-head">
                <strong>Question {{ question.numero || index + 1 }}</strong>
                <input v-model.number="question.points" class="points-input" type="number" min="0" step="0.5" />
              </div>
              <textarea v-model="question.enonce" class="input-control" rows="2" />
              <input v-model="question.type" class="input-control" placeholder="Type de question" />
              <div v-if="question.choix?.length" class="choice-edit-list">
                <input v-for="(_choice, choiceIndex) in question.choix" :key="choiceIndex" v-model="question.choix[choiceIndex]" class="input-control" />
              </div>
              <input v-model="question.bonne_reponse" class="input-control" placeholder="Bonne reponse" />
            </article>
          </div>

          <div v-else class="exam-modal-preview">
            <article v-for="(question, index) in examQuestions(selectedTeacherExam).slice(0, 4)" :key="question.numero || index">
              <strong>Question {{ question.numero || index + 1 }}</strong>
              <p>{{ questionText(question) }}</p>
            </article>
            <p v-if="examQuestions(selectedTeacherExam).length > 4" class="helper-text">
              + {{ examQuestions(selectedTeacherExam).length - 4 }} autres questions.
            </p>
          </div>

          <section v-if="examApproval(selectedTeacherExam).audit_report" class="approval-audit-report">
            <div class="section-title compact-title">
              <ShieldCheck :size="18" />
              <h3>Rapport pedagogique automatique</h3>
              <span v-if="examApproval(selectedTeacherExam).audit_report.score_sur_100 !== undefined" class="status-pill">
                {{ examApproval(selectedTeacherExam).audit_report.score_sur_100 }} / 100
              </span>
            </div>
            <p>
              <strong>Recommandation agent :</strong>
              {{ examApproval(selectedTeacherExam).audit_report.recommendation || examApproval(selectedTeacherExam).audit_report.decision || "Non renseignee" }}
            </p>
            <p>{{ examApproval(selectedTeacherExam).audit_report.resume || examApproval(selectedTeacherExam).audit_report.summary || "Rapport recu." }}</p>
            <ul v-if="examApproval(selectedTeacherExam).audit_report.problemes_detectes?.length">
              <li v-for="problem in examApproval(selectedTeacherExam).audit_report.problemes_detectes" :key="JSON.stringify(problem)">
                {{ typeof problem === "string" ? problem : (problem.description || problem.message || JSON.stringify(problem)) }}
              </li>
            </ul>
          </section>
          <p v-else-if="examApprovalStatus(selectedTeacherExam) === 'pending'" class="helper-text">
            Audit automatique : {{ examApproval(selectedTeacherExam).audit_status === "launch_failed" ? "echec du lancement" : "en cours" }}.
          </p>
          <p v-if="examApprovalStatus(selectedTeacherExam) === 'rejected' && examApproval(selectedTeacherExam).review_reason" class="error-banner compact-banner">
            Motif : {{ examApproval(selectedTeacherExam).review_reason }}
          </p>

          <div class="draft-actions">
            <button v-if="!isAdmin && !isEditingTeacherExam && examApprovalStatus(selectedTeacherExam) !== 'pending'" class="btn btn-secondary" type="button" @click="handleEditPublishedExam(selectedTeacherExam)">
              <Pencil :size="18" />
              <span>Modifier</span>
            </button>
            <button v-if="isEditingTeacherExam" class="btn btn-secondary" type="button" @click="cancelTeacherExamEdit">
              <X :size="18" />
              <span>Annuler</span>
            </button>
            <button v-if="isEditingTeacherExam" class="btn btn-success" type="button" @click="saveTeacherExamEdit">
              <Save :size="18" />
              <span>Enregistrer</span>
            </button>
            <button v-if="!isAdmin && !isEditingTeacherExam && examApprovalStatus(selectedTeacherExam) === 'approved'" class="btn btn-secondary" type="button" @click="handleToggleExamVisibility(selectedTeacherExam)">
              <EyeOff v-if="selectedTeacherExam.status === 'published'" :size="18" />
              <Eye v-else :size="18" />
              <span>{{ selectedTeacherExam.status === "published" ? "Retirer des etudiants" : "Publier aux etudiants" }}</span>
            </button>
            <button
              v-if="isAdmin && examApprovalStatus(selectedTeacherExam) === 'pending'"
              class="btn btn-success"
              type="button"
              :disabled="isReviewingExamApproval || !examApproval(selectedTeacherExam).audit_report"
              :title="!examApproval(selectedTeacherExam).audit_report ? 'Attendre le rapport automatique' : 'Confirmer cet examen'"
              @click="handleReviewExamApproval(selectedTeacherExam, 'approve')"
            >
              <ShieldCheck :size="18" />
              <span>Confirmer pour l'enseignant</span>
            </button>
            <button v-if="isAdmin && examApprovalStatus(selectedTeacherExam) === 'pending'" class="btn btn-danger" type="button" :disabled="isReviewingExamApproval" @click="handleReviewExamApproval(selectedTeacherExam, 'reject')">
              <X :size="18" />
              <span>Ne pas confirmer</span>
            </button>
            <button v-if="!isEditingTeacherExam" class="btn btn-danger" type="button" @click="handleDeletePublishedExam(selectedTeacherExam)">
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
                    v-model="studentAnswers[question.numero || question.number || index + 1]"
                    type="radio"
                    :name="`question-${question.numero || question.number || index + 1}`"
                    :value="choice"
                    :disabled="studentExamSubmitted"
                  />
                  <span class="choice-letter">{{ String.fromCharCode(65 + choiceIndex) }}</span>
                  <span>{{ choice }}</span>
                </label>
              </div>

              <textarea
                v-else
                v-model="studentAnswers[question.numero || question.number || index + 1]"
                class="input-control"
                rows="3"
                placeholder="Ecris ta reponse..."
                :disabled="studentExamSubmitted"
              />
            </article>

            <p v-if="studentExamMessage" class="helper-text">{{ studentExamMessage }}</p>

            <div class="draft-actions">
              <button class="btn btn-secondary" type="button" @click="closeStudentExam">Fermer</button>
              <button v-if="!studentExamSubmitted" class="btn btn-success" type="submit" :disabled="isSubmittingStudentExam">
                <Save :size="18" />
                <span>{{ isSubmittingStudentExam ? "Enregistrement..." : "Soumettre les reponses" }}</span>
              </button>
            </div>
          </form>
        </section>
      </div>

      <div v-if="selectedGradeAttempt" class="modal-backdrop" @click.self="closeGradeDetails">
        <section class="admin-modal exam-take-modal">
          <div class="modal-header">
            <div>
              <span class="eyebrow">DETAIL DE LA CORRECTION</span>
              <h2>
                {{ selectedGradeAttempt.exam_title || publishedExams.find((exam) => exam.id === selectedGradeAttempt.exam_id)?.title || "Examen" }}
              </h2>
            </div>
            <button class="icon-button" type="button" aria-label="Fermer" @click="closeGradeDetails">
              <X :size="18" />
            </button>
          </div>

          <div class="exam-detail-summary">
            <span class="status-pill success">
              Note : {{ selectedGradeAttempt.score ?? 0 }} / {{ selectedGradeAttempt.max_score ?? 0 }}
            </span>
            <span>{{ selectedGradeAttempt.feedback_global || "Correction terminee." }}</span>
            <span v-if="selectedGradeAttempt.student_name">
              {{ selectedGradeAttempt.student_name }} - {{ selectedGradeAttempt.target_study_level }}
            </span>
          </div>

          <div class="student-exam-form">
            <article
              v-for="answer in selectedGradeAttempt.answers"
              :key="answer.question_number"
              class="student-question"
            >
              <div class="question-head">
                <strong>Question {{ answer.question_number }}</strong>
                <span class="status-pill">
                  {{ answer.points_obtained ?? 0 }} / {{ answer.max_points ?? 0 }} pts
                </span>
              </div>
              <p>{{ answer.question_text }}</p>
              <div class="grade-answer-grid">
                <div>
                  <span>{{ selectedGradeAttempt.student_name ? "Reponse de l'etudiant" : "Ma reponse" }}</span>
                  <strong>{{ answer.student_answer || "Aucune reponse" }}</strong>
                </div>
                <div>
                  <span>Reponse attendue</span>
                  <strong>{{ answer.correct_answer || "Non renseignee" }}</strong>
                </div>
                <div class="grade-feedback">
                  <span>Justification de l'agent</span>
                  <strong>{{ answer.feedback || "Aucun commentaire." }}</strong>
                </div>
              </div>
            </article>
          </div>

          <div class="draft-actions">
            <button class="btn btn-secondary" type="button" @click="closeGradeDetails">Fermer</button>
          </div>
        </section>
      </div>

      <section v-if="activePage === 'dashboard'" class="dashboard-page">
        <div v-if="!isStudent" class="dashboard-filter-bar">
          <div>
            <strong>Vue pedagogique de la classe</strong>
            <span>Indicateurs anonymises calcules depuis les examens corriges.</span>
          </div>
          <label>
            <span>Classe</span>
            <select v-model="dashboardStudyLevel" class="input-control" @change="refreshDashboardMetrics">
              <option v-for="level in studyLevels" :key="level" :value="level">{{ level }}</option>
            </select>
          </label>
          <label>
            <span>Annee universitaire</span>
            <input
              v-model.trim="dashboardAcademicYear"
              class="input-control"
              placeholder="2025-2026"
              @change="refreshDashboardMetrics"
            />
          </label>
          <button class="btn btn-secondary" type="button" :disabled="isLoadingDashboard" @click="refreshDashboardMetrics">
            <BarChart3 :size="18" />
            <span>{{ isLoadingDashboard ? "Chargement..." : "Actualiser" }}</span>
          </button>
        </div>

        <div class="metric-grid">
          <article v-for="card in dashboardCards" :key="card.label" class="metric-card" :class="card.tone">
            <span>{{ card.label }}</span>
            <strong>{{ card.value }}</strong>
          </article>
        </div>

        <p
          v-if="dashboardMetrics?.data_status === 'INSUFFICIENT_DATA'"
          class="dashboard-data-warning"
        >
          Echantillon encore faible : les tendances sont indicatives jusqu'a au moins 5 tentatives corrigees.
        </p>

        <article v-if="dashboardMetrics?.latest_report" class="dashboard-latest-report">
          <div>
            <span>Dernier rapport Agentic</span>
            <strong>{{ dashboardMetrics.latest_report.decision || dashboardMetrics.latest_report.status }}</strong>
          </div>
          <p>{{ dashboardMetrics.latest_report.report?.summary || "Rapport pedagogique disponible." }}</p>
          <small>{{ formatDateTime(dashboardMetrics.latest_report.created_at) }}</small>
        </article>

        <div v-if="dashboardMetrics" class="dashboard-analytics-grid">
          <section class="analytics-panel">
            <div class="section-title">
              <BarChart3 :size="19" />
              <h2>Moyenne par examen</h2>
            </div>
            <div v-if="dashboardMetrics.exam_performance.length" class="exam-average-chart">
              <div v-for="exam in dashboardMetrics.exam_performance" :key="exam.exam_id" class="exam-average-column">
                <span class="exam-average-value">{{ exam.average_percent }} %</span>
                <div class="exam-average-bar">
                  <span :style="{ height: `${Math.max(4, Math.min(100, exam.average_percent))}%` }"></span>
                </div>
                <strong :title="exam.title">{{ exam.title }}</strong>
                <small>{{ exam.attempt_count }} tentative(s)</small>
              </div>
            </div>
            <div v-else class="empty-state">Aucun examen corrige pour cette periode.</div>
          </section>

          <section class="analytics-panel difficult-questions-panel">
            <div class="section-title">
              <BookOpenCheck :size="19" />
              <h2>Questions a renforcer</h2>
              <span class="status-pill">Taux de reussite le plus faible</span>
            </div>
            <div v-if="dashboardMetrics.difficult_questions.length" class="difficult-question-list">
              <article v-for="question in dashboardMetrics.difficult_questions" :key="`${question.exam_id}-${question.question_number}`">
                <span>Question {{ question.question_number }}</span>
                <strong>{{ question.question_text }}</strong>
                <b :class="{ critical: question.success_rate < 50 }">{{ question.success_rate }} %</b>
              </article>
            </div>
            <div v-else class="empty-state">Aucune question corrigee pour cette periode.</div>
          </section>
        </div>
      </section>

      <AgentObservabilityDashboard
        v-else-if="activePage === 'agent-observability' && isAdmin"
        :data="agentTelemetryDashboard"
        :loading="isLoadingAgentTelemetry"
        :period="agentTelemetryPeriod"
        @refresh="refreshAgentTelemetryDashboard"
        @update:period="updateAgentTelemetryPeriod"
      />

      <section v-else-if="activePage === 'teacher-exams'" class="panel">
        <div class="section-title">
          <BookOpenCheck :size="19" />
          <h2>Mes examens</h2>
          <span class="status-pill">Gestion enseignant</span>
          <button class="icon-button" type="button" title="Actualiser" aria-label="Actualiser les examens" @click="refreshPublishedExams">
            <RefreshCw :size="17" />
          </button>
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
              {{ examApprovalLabel(exam) }}
            </span>
          </article>
        </div>
      </section>

      <section v-else-if="activePage === 'exam-approvals' && isAdmin" class="panel">
        <div class="section-title">
          <ShieldCheck :size="19" />
          <h2>Validation administrative des examens</h2>
          <span class="status-pill">{{ adminApprovalExams.filter((exam) => examApprovalStatus(exam) === 'pending').length }} en attente</span>
          <button class="icon-button" type="button" title="Actualiser" aria-label="Actualiser les validations" @click="refreshPublishedExams">
            <RefreshCw :size="17" />
          </button>
        </div>

        <div v-if="!adminApprovalExams.length" class="empty-state">
          Aucun examen soumis a l'administration.
        </div>
        <div v-else class="published-exam-list">
          <article
            v-for="exam in adminApprovalExams"
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
            <span class="status-pill" :class="{ success: examApprovalStatus(exam) === 'approved' }">
              {{ examApprovalLabel(exam) }}
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
        <div v-if="studentPublishedExams.length" class="published-exam-list">
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
            <span class="status-pill" :class="{ success: !studentAttemptsByExamId[exam.id] }">
              <PlayCircle :size="14" />
              {{ studentAttemptsByExamId[exam.id] ? "Voir mes reponses" : "Commencer" }}
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

        <div v-if="!gradedStudentAttempts.length" class="empty-state">
          Aucune note publiee pour le moment.
        </div>
        <div v-else class="published-exam-list">
          <article
            v-for="attempt in gradedStudentAttempts"
            :key="attempt.id"
            class="published-exam-card clickable-card"
            role="button"
            tabindex="0"
            @click="openGradeDetails(attempt)"
            @keydown.enter="openGradeDetails(attempt)"
          >
            <div>
              <strong>
                {{ publishedExams.find((exam) => exam.id === attempt.exam_id)?.title || "Examen" }}
              </strong>
              <span>{{ attempt.feedback_global || "Correction terminee." }}</span>
              <small>{{ formatDateTime(attempt.graded_at || attempt.submitted_at) }}</small>
            </div>
            <span class="status-pill success">
              {{ attempt.score ?? 0 }} / {{ attempt.max_score ?? 0 }}
            </span>
          </article>
        </div>
      </section>

      <section v-else-if="activePage === 'resources'" class="panel">
        <div class="section-title">
          <Library :size="19" />
          <h2>Ressources de classe</h2>
          <span class="status-pill">{{ isStudent ? displayStudyLevel || "Etudiant" : "Enseignant" }}</span>
        </div>

        <form
          v-if="canManagePedagogy"
          class="resource-upload-form"
          @submit.prevent="handleUploadClassResource"
        >
          <label>
            <span class="field-label">Titre</span>
            <input v-model.trim="resourceForm.title" class="input-control" placeholder="Ex. Chapitre 2 - Les contrats" />
          </label>
          <label>
            <span class="field-label">Classe destinataire</span>
            <select v-model="resourceForm.target_study_level" class="input-control">
              <option v-for="level in studyLevels" :key="level" :value="level">{{ level }}</option>
            </select>
          </label>
          <label>
            <span class="field-label">PDF ou image</span>
            <input
              ref="resourceFileInput"
              class="input-control file-control"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,application/pdf,image/*"
              @change="handleResourceFile"
            />
          </label>
          <label class="span-2">
            <span class="field-label">Description</span>
            <textarea v-model.trim="resourceForm.description" class="input-control" rows="3" placeholder="Courte description du support" />
          </label>
          <button class="btn btn-primary" type="submit" :disabled="isUploadingResource">
            <Library :size="18" />
            <span>{{ isUploadingResource ? "Envoi..." : "Publier pour la classe" }}</span>
          </button>
        </form>

        <p v-if="resourceMessage" class="helper-text">{{ resourceMessage }}</p>

        <div v-if="isLoadingResources" class="empty-state">Chargement des ressources...</div>
        <div v-else-if="!classResources.length" class="empty-state">
          {{ isStudent ? "Aucune ressource publiee pour ta classe." : "Aucune ressource publiee." }}
        </div>
        <div v-else class="resource-list">
          <article
            v-for="resource in classResources"
            :key="resource.id"
            class="resource-row"
          >
            <button type="button" @click="openClassResource(resource)">
              <span class="resource-file-icon">
                <FileText :size="22" />
              </span>
              <span class="resource-copy">
                <strong>{{ resource.title }}</strong>
                <span>{{ resource.description || resource.filename }}</span>
                <small>{{ resource.target_study_level }} · {{ formatFileSize(resource.size_bytes) }} · {{ formatDateTime(resource.created_at) }}</small>
              </span>
              <span class="status-pill">Ouvrir</span>
            </button>
            <button
              v-if="canManagePedagogy"
              class="icon-button danger"
              type="button"
              aria-label="Supprimer la ressource"
              @click="handleDeleteClassResource(resource)"
            >
              <Trash2 :size="17" />
            </button>
          </article>
        </div>
      </section>

      <section v-else-if="activePage === 'staff-results'" class="panel">
        <div class="section-title">
          <NotebookPen :size="19" />
          <h2>Resultats des etudiants</h2>
          <span class="status-pill">Lecture seule</span>
        </div>

        <div class="table-toolbar">
          <label>
            <span class="field-label">Classe</span>
            <select
              v-model="staffResultsStudyLevel"
              class="input-control"
              @change="refreshStaffResults"
            >
              <option value="">Toutes les classes</option>
              <option v-for="level in studyLevels" :key="level" :value="level">{{ level }}</option>
            </select>
          </label>
          <button class="btn btn-secondary" type="button" :disabled="isLoadingStaffResults" @click="refreshStaffResults">
            <NotebookPen :size="18" />
            <span>{{ isLoadingStaffResults ? "Chargement..." : "Actualiser" }}</span>
          </button>
        </div>

        <div v-if="!staffResults.length" class="empty-state">
          Aucun resultat note pour cette classe.
        </div>
        <div v-else class="published-exam-list">
          <article
            v-for="result in staffResults"
            :key="result.id"
            class="published-exam-card clickable-card"
            role="button"
            tabindex="0"
            @click="openGradeDetails(result)"
            @keydown.enter="openGradeDetails(result)"
          >
            <div>
              <strong>{{ result.student_name }}</strong>
              <span>{{ result.module }} - {{ result.target_study_level }}</span>
              <small>{{ result.exam_title }} - {{ formatDateTime(result.graded_at) }}</small>
            </div>
            <span class="status-pill success">
              {{ result.score ?? 0 }} / {{ result.max_score ?? 0 }}
            </span>
          </article>
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
            <KnowledgeBaseUploader
              ref="knowledgeBaseUploader"
              :access-token="session.access_token"
              @created="handleKnowledgeBaseCreated"
            />
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

        <AgendaCalendar
          :items="agendaItems"
          :empty-label="
            isStudent
              ? `Aucun evenement pour ton niveau (${displayStudyLevel || 'niveau non defini'}).`
              : 'Aucun evenement cree. Ajoute le premier evenement pour une classe.'
          "
        />
      </section>

      <section v-else-if="activePage === 'pedagogical-analysis'" class="panel">
        <div class="section-title">
          <BarChart3 :size="19" />
          <h2>Analyse pedagogique</h2>
          <span class="status-pill">Administration</span>
        </div>

        <div class="pedagogical-report-layout">
          <form class="pedagogical-report-form" @submit.prevent="handleLaunchPedagogicalReport">
            <label>
              <span class="field-label">Classe</span>
              <select v-model="pedagogicalReportForm.study_level" class="input-control">
                <option v-for="level in studyLevels" :key="level" :value="level">{{ level }}</option>
              </select>
            </label>

            <label>
              <span class="field-label">Annee universitaire</span>
              <input
                v-model.trim="pedagogicalReportForm.academic_year"
                class="input-control"
                placeholder="Ex. 2026-2027"
                required
              />
            </label>

            <button class="btn btn-primary" type="submit" :disabled="isLaunchingPedagogicalReport">
              <BarChart3 :size="18" />
              <span>{{ isLaunchingPedagogicalReport ? "Lancement..." : "Lancer l'analyse" }}</span>
            </button>
          </form>

          <section class="pedagogical-report-status">
            <strong>Suivi du workflow</strong>
            <p v-if="pedagogicalReportMessage" class="helper-text">{{ pedagogicalReportMessage }}</p>
            <div v-if="pedagogicalReportRun" class="report-run-summary">
              <span class="status-pill success">{{ pedagogicalReportRun.status }}</span>
              <dl>
                <div>
                  <dt>Correlation ID</dt>
                  <dd>{{ pedagogicalReportRun.correlation_id }}</dd>
                </div>
                <div>
                  <dt>Reponse Agentic</dt>
                  <dd>
                    {{ pedagogicalReportRun.workflow_response?.message || pedagogicalReportRun.workflow_response?.status || "Workflow accepte" }}
                  </dd>
                </div>
              </dl>

              <article v-if="pedagogicalReportResult" class="pedagogical-report-result">
                <div class="report-result-heading">
                  <strong>Rapport final</strong>
                  <span v-if="pedagogicalReportResult.score_sur_100 !== undefined" class="status-pill">
                    {{ pedagogicalReportResult.score_sur_100 }} / 100
                  </span>
                </div>
                <p v-if="pedagogicalReportResult.decision">
                  <strong>Decision :</strong> {{ pedagogicalReportResult.decision }}
                </p>
                <p v-if="pedagogicalReportResult.resume">
                  {{ pedagogicalReportResult.resume }}
                </p>
                <div
                  v-if="pedagogicalReportResult.summary && typeof pedagogicalReportResult.summary === 'object'"
                  class="report-summary-grid"
                >
                  <div>
                    <span>Examens analyses</span>
                    <strong>{{ pedagogicalReportResult.summary.exam_count ?? 0 }}</strong>
                  </div>
                  <div>
                    <span>Tentatives analysees</span>
                    <strong>{{ pedagogicalReportResult.summary.attempt_count ?? 0 }}</strong>
                  </div>
                </div>
                <p v-else-if="pedagogicalReportResult.summary">
                  {{ pedagogicalReportResult.summary }}
                </p>

                <section v-if="pedagogicalReportResult.strengths?.length" class="report-detail-section">
                  <strong>Points forts</strong>
                  <ul>
                    <li v-for="strength in pedagogicalReportResult.strengths" :key="JSON.stringify(strength)">
                      <div class="report-list-heading">
                        <strong>{{ strength.concept || "Notion maitrisee" }}</strong>
                        <span v-if="strength.success_rate !== undefined">{{ strength.success_rate }} %</span>
                      </div>
                      <p v-if="strength.evidence">{{ strength.evidence }}</p>
                    </li>
                  </ul>
                </section>

                <section v-if="pedagogicalReportResult.difficulties?.length" class="report-detail-section">
                  <strong>Difficultes</strong>
                  <ul>
                    <li v-for="difficulty in pedagogicalReportResult.difficulties" :key="JSON.stringify(difficulty)">
                      <div class="report-list-heading">
                        <strong>{{ difficulty.concept || "Notion a renforcer" }}</strong>
                        <span v-if="difficulty.success_rate !== undefined">{{ difficulty.success_rate }} %</span>
                      </div>
                      <p v-if="difficulty.evidence">{{ difficulty.evidence }}</p>
                    </li>
                  </ul>
                </section>

                <section v-if="pedagogicalReportResult.recommendations?.length" class="report-detail-section">
                  <strong>Recommandations</strong>
                  <ul>
                    <li v-for="recommendation in pedagogicalReportResult.recommendations" :key="JSON.stringify(recommendation)">
                      <div class="report-list-heading">
                        <strong>{{ recommendation.concept || "Action pedagogique" }}</strong>
                        <span v-if="recommendation.priority">Priorite {{ recommendation.priority }}</span>
                      </div>
                      <p>{{ recommendation.action || recommendation.description || recommendation }}</p>
                    </li>
                  </ul>
                </section>

                <section v-if="pedagogicalReportResult.data_limits?.length" class="report-detail-section">
                  <strong>Limites des donnees</strong>
                  <ul>
                    <li v-for="limit in pedagogicalReportResult.data_limits" :key="JSON.stringify(limit)">{{ limit }}</li>
                  </ul>
                </section>
                <div v-if="pedagogicalReportResult.problemes_detectes?.length">
                  <strong>Problemes detectes</strong>
                  <ul>
                    <li v-for="problem in pedagogicalReportResult.problemes_detectes" :key="JSON.stringify(problem)">
                      {{ typeof problem === "string" ? problem : (problem.description || problem.message || JSON.stringify(problem)) }}
                    </li>
                  </ul>
                </div>
                <div v-if="pedagogicalReportResult.corrections_recommandees?.length">
                  <strong>Corrections recommandees</strong>
                  <ul>
                    <li v-for="correction in pedagogicalReportResult.corrections_recommandees" :key="JSON.stringify(correction)">
                      {{ typeof correction === "string" ? correction : (correction.description || correction.message || JSON.stringify(correction)) }}
                    </li>
                  </ul>
                </div>
              </article>
            </div>
            <div v-else class="empty-state">
              Configure l'analyse puis lance le workflow pour verifier son routage.
            </div>
          </section>
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
