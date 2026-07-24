<script setup>
import { CheckCircle2, RefreshCw, Send, Sparkles } from "lucide-vue-next";

defineProps({
  exam: {
    type: Object,
    required: true,
  },
  isPublishing: Boolean,
  publishMessage: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["regenerate", "publish"]);

function questionId(question, index) {
  return question.id ?? question.numero ?? index + 1;
}

function questionTitle(question, index) {
  return question.intitule || question.title || `Question ${questionId(question, index)}`;
}

function questionText(question) {
  return question.texte || question.enonce || question.prompt || "";
}

function questionPoints(question) {
  return question.bareme ?? question.points ?? 0;
}

function questionChoices(question) {
  const choices = question.choix || question.options || question.propositions || question.answers || [];
  return Array.isArray(choices) ? choices : [];
}

function correctAnswer(question) {
  return question.bonne_reponse || question.correct_answer || question.reponse_correcte || "";
}

function examTotal(exam) {
  const explicitTotal =
    exam.bareme_total ?? exam["barème_total"] ?? exam["barÃ¨me_total"] ?? exam.total_points;

  if (explicitTotal !== undefined && explicitTotal !== null) {
    return explicitTotal;
  }

  return (exam.questions || []).reduce((sum, question) => sum + Number(questionPoints(question) || 0), 0);
}
</script>

<template>
  <section class="panel exam-draft">
    <div class="section-title">
      <Sparkles :size="19" />
      <h2>Brouillon genere par l'agent</h2>
      <span class="status-pill">Validation enseignant</span>
    </div>

    <div class="draft-header">
      <div>
        <strong>{{ exam.module || "Examen genere" }}</strong>
        <span>{{ exam.type_evaluation || exam.evaluation_type || "Evaluation" }} - {{ exam.niveau || exam.study_level }}</span>
      </div>
      <div class="draft-stats">
        <span>{{ exam.questions?.length || 0 }} questions</span>
        <span>{{ examTotal(exam) }} points</span>
      </div>
    </div>

    <div class="question-list">
      <article v-for="(question, index) in exam.questions" :key="questionId(question, index)" class="question-card">
        <div class="question-head">
          <strong>{{ questionTitle(question, index) }}</strong>
          <span class="status-pill">{{ questionPoints(question) }} pts</span>
        </div>
        <p>{{ questionText(question) }}</p>
        <ol v-if="questionChoices(question).length" class="choice-list">
          <li v-for="(choice, choiceIndex) in questionChoices(question)" :key="`${questionId(question, index)}-${choiceIndex}`">
            <span class="choice-letter">{{ String.fromCharCode(65 + choiceIndex) }}</span>
            <span>{{ choice }}</span>
          </li>
        </ol>
        <p v-if="correctAnswer(question)" class="correct-answer">
          Bonne reponse : {{ correctAnswer(question) }}
        </p>
        <small v-if="question.type">{{ question.type }}</small>
      </article>
    </div>

    <div class="draft-actions">
      <button class="btn btn-secondary" type="button" @click="emit('regenerate')">
        <RefreshCw :size="18" />
        <span>Regenerer</span>
      </button>
      <button class="btn btn-success" type="button" :disabled="isPublishing" @click="emit('publish')">
        <Send :size="18" />
        <span>{{ isPublishing ? "Envoi..." : "Soumettre a l'administration" }}</span>
      </button>
    </div>

    <p v-if="publishMessage" class="helper-text publish-message">
      <CheckCircle2 :size="17" />
      <span>{{ publishMessage }}</span>
    </p>
  </section>
</template>
