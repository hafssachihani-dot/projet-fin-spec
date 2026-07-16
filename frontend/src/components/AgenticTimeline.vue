<script setup>
import { CheckCircle2, Route } from "lucide-vue-next";

defineProps({
  steps: {
    type: Array,
    required: true
  }
});
</script>

<template>
  <section class="panel">
    <div class="section-title">
      <Route :size="19" />
      <h2>Orchestration Agentic RAG</h2>
      <span class="status-pill">Trace</span>
    </div>
    <ol class="timeline">
      <li v-for="step in steps" :key="step.name">
        <CheckCircle2 :size="18" />
        <div>
          <strong>{{ step.name }}</strong>
          <p>{{ step.detail }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>

