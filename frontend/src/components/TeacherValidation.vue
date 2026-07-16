<script setup>
import { CheckCircle2, UserCheck } from "lucide-vue-next";
import { ref } from "vue";

defineProps({
  exam: {
    type: Object,
    required: true
  },
  isPublishing: Boolean
});

const emit = defineEmits(["publish"]);
const teacherNote = ref("");
</script>

<template>
  <section class="panel">
    <div class="section-title">
      <UserCheck :size="19" />
      <h2>Human-in-the-Loop</h2>
      <span class="status-pill">Validation</span>
    </div>

    <ul class="bullet-list">
      <li>Modifier une question</li>
      <li>Supprimer une question</li>
      <li>Régénérer une question</li>
      <li>Changer le barème</li>
      <li>Ajouter une remarque</li>
    </ul>

    <label class="field-label" for="teacher-note">Remarque enseignant</label>
    <textarea id="teacher-note" v-model="teacherNote" class="input-control" rows="3" />

    <div class="action-row">
      <div>
        <strong>Bouton principal</strong>
        <p>Valider et publier l’examen</p>
      </div>
      <button class="btn btn-success" type="button" :disabled="exam.status === 'published' || isPublishing" @click="emit('publish', teacherNote)">
        <CheckCircle2 :size="18" />
        <span>{{ exam.status === "published" ? "Publié" : "Valider et publier" }}</span>
      </button>
    </div>
  </section>
</template>

