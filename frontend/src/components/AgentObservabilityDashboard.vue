<script setup>
import { computed } from "vue";
import {
  Activity,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Gauge,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
} from "lucide-vue-next";

const props = defineProps({
  data: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  period: {
    type: Number,
    default: 30,
  },
});

const emit = defineEmits(["refresh", "update:period"]);

const summary = computed(() => props.data?.summary || {});
const agents = computed(() => props.data?.agents || []);
const trend = computed(() => props.data?.daily_trend || []);
const recentEvents = computed(() => props.data?.recent_events || []);

const metricCards = computed(() => [
  {
    label: "Executions analysees",
    value: summary.value.total_executions ?? 0,
    detail: `${agents.value.length} agent(s) observe(s)`,
    tone: "blue",
    icon: Activity,
  },
  {
    label: "Taux de succes",
    value: formatPercent(summary.value.success_rate),
    detail: "Executions sans erreur systeme",
    tone: "green",
    icon: CheckCircle2,
  },
  {
    label: "Qualite validee",
    value: formatPercent(summary.value.quality_pass_rate),
    detail: "Evaluations ayant passe le seuil",
    tone: "violet",
    icon: ShieldCheck,
  },
  {
    label: "Score qualite",
    value: formatPercent(summary.value.quality_score),
    detail: "Score composite du harness",
    tone: "cyan",
    icon: Gauge,
  },
  {
    label: "Hallucination",
    value: formatPercent(summary.value.hallucination_score),
    detail: "Plus faible est meilleur",
    tone: Number(summary.value.hallucination_score || 0) > 20 ? "red" : "amber",
    icon: TriangleAlert,
  },
]);

const qualityMetrics = computed(() => [
  { label: "Exactitude", value: summary.value.accuracy, color: "#2563eb" },
  { label: "Fidelite au contexte", value: summary.value.faithfulness, color: "#0f9f75" },
  { label: "Respect des consignes", value: summary.value.instruction_following, color: "#7c3aed" },
  { label: "Pertinence", value: summary.value.answer_relevancy, color: "#0891b2" },
]);

function formatPercent(value) {
  return value === null || value === undefined ? "--" : `${Number(value).toFixed(1)} %`;
}

function formatLatency(value) {
  if (value === null || value === undefined) return "Non mesuree";
  if (Number(value) >= 1000) return `${(Number(value) / 1000).toFixed(2)} s`;
  return `${Math.round(Number(value))} ms`;
}

function formatDate(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDay(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" }).format(
    new Date(`${value}T12:00:00`)
  );
}

function statusLabel(event) {
  if (!event.success) return "Erreur";
  return event.quality_passed ? "Valide" : "A verifier";
}
</script>

<template>
  <section class="agent-observability-page">
    <header class="observability-toolbar">
      <div>
        <span class="observability-eyebrow">HARNESS INDEPENDANT</span>
        <h2>Observabilite des agents</h2>
        <p>Performance et qualite mesurees sur les executions reelles des workflows.</p>
      </div>
      <div class="observability-actions">
        <label>
          <span>Periode</span>
          <select
            :value="period"
            class="input-control"
            @change="emit('update:period', Number($event.target.value))"
          >
            <option :value="7">7 derniers jours</option>
            <option :value="30">30 derniers jours</option>
            <option :value="90">90 derniers jours</option>
            <option :value="365">12 derniers mois</option>
          </select>
        </label>
        <button class="btn btn-secondary" type="button" :disabled="loading" @click="emit('refresh')">
          <RefreshCw :size="17" :class="{ spinning: loading }" />
          <span>{{ loading ? "Actualisation..." : "Actualiser" }}</span>
        </button>
      </div>
    </header>

    <div v-if="!data && loading" class="observability-empty">Chargement des mesures...</div>

    <template v-else>
      <div class="observability-metrics">
        <article v-for="card in metricCards" :key="card.label" class="observability-metric" :class="card.tone">
          <div>
            <span>{{ card.label }}</span>
            <component :is="card.icon" :size="18" />
          </div>
          <strong>{{ card.value }}</strong>
          <small>{{ card.detail }}</small>
        </article>
      </div>

      <div v-if="!summary.total_executions" class="observability-empty">
        Aucun evenement sur cette periode. Lance une generation ou une correction avec le harness active.
      </div>

      <div v-else class="observability-primary-grid">
        <section class="observability-panel">
          <div class="observability-panel-title">
            <BrainCircuit :size="19" />
            <div>
              <h3>Qualite des sorties</h3>
              <span>Moyennes calculees par l'evaluateur independant</span>
            </div>
          </div>
          <div class="quality-bars">
            <div v-for="metric in qualityMetrics" :key="metric.label" class="quality-row">
              <div>
                <span>{{ metric.label }}</span>
                <strong>{{ formatPercent(metric.value) }}</strong>
              </div>
              <div class="quality-track">
                <span
                  :style="{
                    width: `${Math.max(0, Math.min(100, Number(metric.value || 0)))}%`,
                    backgroundColor: metric.color,
                  }"
                ></span>
              </div>
            </div>
          </div>
        </section>

        <section class="observability-panel system-health-panel">
          <div class="observability-panel-title">
            <Clock3 :size="19" />
            <div>
              <h3>Sante du workflow</h3>
              <span>Mesures externes disponibles</span>
            </div>
          </div>
          <dl class="health-list">
            <div>
              <dt>Latence moyenne</dt>
              <dd>{{ formatLatency(summary.average_latency_ms) }}</dd>
            </div>
            <div>
              <dt>Echantillons de latence</dt>
              <dd>{{ summary.latency_sample_count ?? 0 }}</dd>
            </div>
            <div>
              <dt>Problemes signales</dt>
              <dd :class="{ warning: summary.issue_count > 0 }">{{ summary.issue_count ?? 0 }}</dd>
            </div>
          </dl>
          <p v-if="!summary.latency_sample_count" class="measurement-note">
            La latence apparaitra lorsque le harness enverra le champ <code>latency_ms</code>.
          </p>
        </section>
      </div>

      <section v-if="agents.length" class="observability-panel agent-comparison-panel">
        <div class="observability-panel-title">
          <Activity :size="19" />
          <div>
            <h3>Comparaison des agents</h3>
            <span>Une ligne par agent et workflow</span>
          </div>
        </div>
        <div class="agent-table-wrap">
          <table class="agent-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Workflow</th>
                <th>Executions</th>
                <th>Succes</th>
                <th>Qualite</th>
                <th>Exactitude</th>
                <th>Hallucination</th>
                <th>Latence</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="agent in agents" :key="`${agent.workflow_name}-${agent.agent_name}`">
                <td><strong>{{ agent.agent_name }}</strong></td>
                <td>{{ agent.workflow_name }}</td>
                <td>{{ agent.executions }}</td>
                <td>{{ formatPercent(agent.success_rate) }}</td>
                <td>{{ formatPercent(agent.quality_score) }}</td>
                <td>{{ formatPercent(agent.accuracy) }}</td>
                <td :class="{ warning: agent.hallucination_score > 20 }">
                  {{ formatPercent(agent.hallucination_score) }}
                </td>
                <td>{{ formatLatency(agent.average_latency_ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div class="observability-secondary-grid">
        <section class="observability-panel trend-panel">
          <div class="observability-panel-title">
            <Gauge :size="19" />
            <div>
              <h3>Tendance qualite</h3>
              <span>Score composite par jour</span>
            </div>
          </div>
          <div v-if="trend.length" class="quality-trend">
            <div v-for="item in trend" :key="item.date" class="trend-column">
              <strong>{{ item.quality_score }} %</strong>
              <div class="trend-track">
                <span :style="{ height: `${Math.max(4, item.quality_score)}%` }"></span>
              </div>
              <small>{{ formatDay(item.date) }}</small>
            </div>
          </div>
          <div v-else class="observability-empty compact">Aucune tendance disponible.</div>
        </section>

        <section class="observability-panel recent-panel">
          <div class="observability-panel-title">
            <ShieldCheck :size="19" />
            <div>
              <h3>Dernieres evaluations</h3>
              <span>Resultats les plus recents du harness</span>
            </div>
          </div>
          <div class="recent-evaluation-list">
            <article v-for="event in recentEvents.slice(0, 6)" :key="event.id">
              <div>
                <strong>{{ event.agent_name }}</strong>
                <span>{{ event.workflow_name }} - {{ formatDate(event.created_at) }}</span>
              </div>
              <b>{{ event.quality_score }} %</b>
              <span
                class="evaluation-status"
                :class="{ success: event.success && event.quality_passed, warning: event.success && !event.quality_passed }"
              >
                {{ statusLabel(event) }}
              </span>
            </article>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<style scoped>
.agent-observability-page {
  display: grid;
  gap: 16px;
}

.observability-toolbar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 1px solid #dbe3ee;
  padding: 2px 2px 16px;
}

.observability-toolbar h2,
.observability-panel h3 {
  margin: 0;
  letter-spacing: 0;
}

.observability-toolbar h2 {
  margin-top: 4px;
  font-size: 22px;
}

.observability-toolbar p,
.observability-panel-title span,
.observability-metric small {
  color: #64748b;
}

.observability-toolbar p {
  margin: 5px 0 0;
  font-size: 13px;
}

.observability-eyebrow {
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
}

.observability-actions {
  display: flex;
  align-items: end;
  gap: 10px;
}

.observability-actions label {
  display: grid;
  gap: 5px;
}

.observability-actions label > span {
  color: #64748b;
  font-size: 11px;
}

.observability-actions .input-control {
  min-width: 180px;
}

.observability-metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.observability-metric {
  display: grid;
  gap: 8px;
  min-width: 0;
  border: 1px solid #dbe3ee;
  border-top: 3px solid var(--metric-color);
  border-radius: 7px;
  background: #ffffff;
  padding: 14px;
}

.observability-metric > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--metric-color);
}

.observability-metric > div span {
  color: #475569;
  font-size: 12px;
}

.observability-metric strong {
  font-size: 23px;
}

.observability-metric small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.observability-metric.blue { --metric-color: #2563eb; }
.observability-metric.green { --metric-color: #0f9f75; }
.observability-metric.violet { --metric-color: #7c3aed; }
.observability-metric.cyan { --metric-color: #0891b2; }
.observability-metric.amber { --metric-color: #d97706; }
.observability-metric.red { --metric-color: #dc2626; }

.observability-primary-grid,
.observability-secondary-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.65fr);
  gap: 16px;
}

.observability-secondary-grid {
  grid-template-columns: minmax(320px, 0.8fr) minmax(380px, 1.2fr);
}

.observability-panel {
  min-width: 0;
  border: 1px solid #dbe3ee;
  border-radius: 7px;
  background: #ffffff;
  padding: 16px;
}

.observability-panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 12px;
  margin-bottom: 14px;
  color: #1d4ed8;
}

.observability-panel-title > div {
  display: grid;
  gap: 2px;
}

.observability-panel-title h3 {
  color: #0f172a;
  font-size: 15px;
}

.observability-panel-title span {
  font-size: 11px;
}

.quality-bars,
.health-list,
.recent-evaluation-list {
  display: grid;
  gap: 12px;
}

.quality-row {
  display: grid;
  grid-template-columns: 185px minmax(120px, 1fr);
  align-items: center;
  gap: 14px;
}

.quality-row > div:first-child {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
}

.quality-track {
  height: 9px;
  overflow: hidden;
  border-radius: 5px;
  background: #e2e8f0;
}

.quality-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.health-list {
  margin: 0;
}

.health-list > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #eef2f7;
  padding-bottom: 10px;
}

.health-list dt {
  color: #64748b;
  font-size: 12px;
}

.health-list dd {
  margin: 0;
  font-weight: 800;
}

.warning {
  color: #dc2626;
}

.measurement-note {
  border-left: 3px solid #d97706;
  background: #fffbeb;
  color: #78350f;
  padding: 9px 10px;
  margin: 14px 0 0;
  font-size: 11px;
}

.agent-table-wrap {
  overflow-x: auto;
}

.agent-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.agent-table th,
.agent-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 10px 9px;
  text-align: left;
  white-space: nowrap;
}

.agent-table th {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.quality-trend {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(58px, 1fr);
  align-items: end;
  gap: 8px;
  min-height: 190px;
  overflow-x: auto;
}

.trend-column {
  display: grid;
  grid-template-rows: 20px 130px 20px;
  gap: 5px;
  text-align: center;
}

.trend-column strong,
.trend-column small {
  color: #64748b;
  font-size: 10px;
}

.trend-track {
  display: flex;
  align-items: end;
  justify-content: center;
  border-bottom: 1px solid #cbd5e1;
}

.trend-track span {
  width: 28px;
  min-height: 4px;
  border-radius: 4px 4px 0 0;
  background: #0891b2;
}

.recent-evaluation-list article {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) 54px 72px;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 10px;
}

.recent-evaluation-list article:last-child {
  border-bottom: 0;
}

.recent-evaluation-list article > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.recent-evaluation-list strong,
.recent-evaluation-list span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-evaluation-list strong {
  font-size: 12px;
}

.recent-evaluation-list span {
  color: #64748b;
  font-size: 10px;
}

.evaluation-status {
  border-radius: 4px;
  background: #fee2e2;
  color: #991b1b !important;
  padding: 5px 7px;
  text-align: center;
  font-weight: 700;
}

.evaluation-status.success {
  background: #dcfce7;
  color: #166534 !important;
}

.evaluation-status.warning {
  background: #fef3c7;
  color: #92400e !important;
}

.observability-empty {
  border: 1px dashed #cbd5e1;
  border-radius: 7px;
  background: #f8fafc;
  color: #64748b;
  padding: 36px 18px;
  text-align: center;
}

.observability-empty.compact {
  padding: 22px 14px;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1180px) {
  .observability-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .observability-toolbar,
  .observability-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .observability-metrics,
  .observability-primary-grid,
  .observability-secondary-grid {
    grid-template-columns: 1fr;
  }

  .observability-actions .input-control {
    width: 100%;
  }

  .quality-row,
  .recent-evaluation-list article {
    grid-template-columns: 1fr;
  }
}
</style>
