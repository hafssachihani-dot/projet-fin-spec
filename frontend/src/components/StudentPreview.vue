<script setup>
import { BookOpen, CheckCircle2, CirclePlay, GraduationCap } from "lucide-vue-next";

defineProps({
  exam: {
    type: Object,
    required: true
  }
});
</script>

<template>
  <section class="panel student-panel">
    <div class="section-title">
      <GraduationCap :size="19" />
      <h2>Ce que voit l’étudiant</h2>
      <span class="status-pill success">{{ exam.status === "published" ? "Publié" : "Brouillon" }}</span>
    </div>

    <article class="student-card">
      <div class="exam-heading">
        <BookOpen :size="20" />
        <div>
          <h3>{{ exam.request.module }} - {{ exam.request.evaluation_type }}</h3>
          <p>Publié par : Enseignant</p>
        </div>
        <span class="status-pill success">Disponible</span>
      </div>

      <div class="student-stats">
        <div>
          <span>Date</span>
          <strong>15/07/2026</strong>
        </div>
        <div>
          <span>Durée</span>
          <strong>{{ exam.request.duration }}</strong>
        </div>
        <div>
          <span>Questions</span>
          <strong>{{ exam.questions.length }}</strong>
        </div>
        <div>
          <span>Équité</span>
          <strong>{{ exam.report.equity_score }}%</strong>
        </div>
      </div>

      <div class="student-footer">
        <span>
          <CheckCircle2 :size="17" />
          Examen validé par l’enseignant
        </span>
        <button class="btn btn-light" type="button">
          <CirclePlay :size="17" />
          <span>Commencer l’examen</span>
        </button>
      </div>
    </article>
  </section>
</template>
