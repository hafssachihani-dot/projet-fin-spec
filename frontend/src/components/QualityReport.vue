<script setup>
import { BarChart3, CheckCircle2 } from "lucide-vue-next";

defineProps({
  exam: {
    type: Object,
    required: true
  }
});
</script>

<template>
  <section class="panel">
    <div class="section-title">
      <BarChart3 :size="19" />
      <h2>Rapport qualité</h2>
      <span class="status-pill">{{ exam.report.global_score }}%</span>
    </div>

    <div class="score-grid">
      <div>
        <span>Alignement</span>
        <strong>{{ exam.report.alignment_score }}%</strong>
      </div>
      <div>
        <span>Difficulté</span>
        <strong>{{ exam.report.difficulty_score }}%</strong>
      </div>
      <div>
        <span>Clarté</span>
        <strong>{{ exam.report.clarity_score }}%</strong>
      </div>
      <div>
        <span>Équité</span>
        <strong>{{ exam.report.equity_score }}%</strong>
      </div>
    </div>

    <h3>Corrections appliquées</h3>
    <ul class="check-list">
      <li v-for="item in exam.report.applied_corrections" :key="item">
        <CheckCircle2 :size="16" />
        <span>{{ item }}</span>
      </li>
    </ul>
    <p class="report-note">{{ exam.report.pedagogical_justification }}</p>
  </section>
</template>

