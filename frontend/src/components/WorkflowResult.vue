<script setup>
import { CheckCircle2, Clock, Send, Server } from "lucide-vue-next";

defineProps({
  run: {
    type: Object,
    required: true
  }
});

function pretty(value) {
  return JSON.stringify(value, null, 2);
}
</script>

<template>
  <section class="panel workflow-result">
    <div class="section-title">
      <Server :size="19" />
      <h2>Résultat réel du workflow</h2>
      <span class="status-pill success">{{ run.status }}</span>
    </div>

    <div class="run-summary">
      <div>
        <CheckCircle2 :size="18" />
        <span>Run ID</span>
        <strong>{{ run.run_id }}</strong>
      </div>
      <div>
        <Clock :size="18" />
        <span>Lancé à</span>
        <strong>{{ run.started_at }}</strong>
      </div>
      <div>
        <Send :size="18" />
        <span>Webhook</span>
        <strong>{{ run.webhook_url }}</strong>
      </div>
    </div>

    <h3>Réponse retournée par le workflow</h3>
    <pre class="json-box"><code>{{ pretty(run.workflow_response) }}</code></pre>

    <h3>Payload envoyé au workflow</h3>
    <pre class="json-box"><code>{{ pretty(run.sent_payload) }}</code></pre>
  </section>
</template>
