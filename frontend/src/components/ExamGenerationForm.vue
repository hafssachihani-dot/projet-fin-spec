<script setup>
import { reactive } from "vue";
import { Loader2, Sparkles } from "lucide-vue-next";

defineProps({
  disabled: Boolean,
  isGenerating: Boolean,
});

const emit = defineEmits(["submit"]);

const form = reactive({
  module: "Droit des contrats",
  duration: "2h",
  study_level: "Licence 2",
  difficulty: "Intermediaire",
  evaluation_type: "Examen final",
  question_count: 20,
  learning_objectives:
    "Evaluer la comprehension des conditions de formation du contrat, du consentement, de la capacite juridique, de l'objet du contrat et de la resolution de cas pratiques.",
  constraints:
    "Bareme total sur 20 points. Inclure une question sur le consentement, une question sur la capacite juridique, une question sur l'objet du contrat, un cas pratique sur un vice du consentement et des questions progressives.",
});

function submitForm() {
  emit("submit", { ...form, question_count: Number(form.question_count) });
}
</script>

<template>
  <form class="exam-form" @submit.prevent="submitForm">
    <div class="form-grid">
      <label>
        <span>Module / Matiere</span>
        <input v-model="form.module" class="input-control" placeholder="Ex. Droit des contrats" />
      </label>

      <label>
        <span>Duree</span>
        <input v-model="form.duration" class="input-control" placeholder="Ex. 2h" />
      </label>

      <label>
        <span>Niveau d'etude</span>
        <select v-model="form.study_level" class="input-control">
          <option>Licence 1</option>
          <option>Licence 2</option>
          <option>Licence 3</option>
          <option>Master 1</option>
          <option>Master 2</option>
        </select>
      </label>

      <label>
        <span>Niveau de difficulte souhaite</span>
        <select v-model="form.difficulty" class="input-control">
          <option>Facile</option>
          <option>Intermediaire</option>
          <option>Difficile</option>
          <option>Mixte progressif</option>
        </select>
      </label>

      <label>
        <span>Type d'evaluation</span>
        <select v-model="form.evaluation_type" class="input-control">
          <option>Quiz</option>
          <option>Controle continu</option>
          <option>Examen final</option>
          <option>Etude de cas</option>
        </select>
      </label>

      <label>
        <span>Nombre de questions</span>
        <input v-model="form.question_count" class="input-control" type="number" min="1" max="100" />
      </label>

      <label class="span-2">
        <span>Objectifs pedagogiques</span>
        <textarea v-model="form.learning_objectives" class="input-control" rows="4" />
      </label>

      <label class="span-2">
        <span>Contraintes eventuelles</span>
        <textarea v-model="form.constraints" class="input-control" rows="3" />
      </label>
    </div>

    <div class="action-row">
      <div>
        <strong>Action principale</strong>
        <p>Declenche l'orchestration Agentic RAG</p>
      </div>
      <button class="btn btn-primary" type="submit" :disabled="disabled">
        <Loader2 v-if="isGenerating" :size="18" class="spin" />
        <Sparkles v-else :size="18" />
        <span>{{ isGenerating ? "Generation..." : "Generer l'examen" }}</span>
      </button>
    </div>
  </form>
</template>
