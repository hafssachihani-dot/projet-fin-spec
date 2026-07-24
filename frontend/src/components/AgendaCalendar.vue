<script setup>
import { computed, ref } from "vue";
import { CalendarDays, ChevronLeft, ChevronRight, Clock3, X } from "lucide-vue-next";

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  emptyLabel: {
    type: String,
    default: "Aucun evenement programme.",
  },
});

const weekdays = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const monthCursor = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1));
const selectedDay = ref(null);

const monthLabel = computed(() =>
  new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" }).format(monthCursor.value)
);

function dateKey(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function eventsForDate(date) {
  const key = dateKey(date);
  return props.items.filter((item) => dateKey(item.scheduled_at) === key);
}

function isExam(item) {
  const type = String(item.evaluation_type || "").toLowerCase();
  return type.includes("examen") || type.includes("rattrapage");
}

const calendarDays = computed(() => {
  const year = monthCursor.value.getFullYear();
  const month = monthCursor.value.getMonth();
  const firstDay = new Date(year, month, 1);
  const mondayOffset = (firstDay.getDay() + 6) % 7;
  const start = new Date(year, month, 1 - mondayOffset);
  const todayKey = dateKey(new Date());

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    const events = eventsForDate(date);
    return {
      key: dateKey(date),
      date,
      dayNumber: date.getDate(),
      isCurrentMonth: date.getMonth() === month,
      isToday: dateKey(date) === todayKey,
      events,
      hasExam: events.some(isExam),
    };
  });
});

function changeMonth(offset) {
  monthCursor.value = new Date(
    monthCursor.value.getFullYear(),
    monthCursor.value.getMonth() + offset,
    1
  );
  selectedDay.value = null;
}

function goToToday() {
  const today = new Date();
  monthCursor.value = new Date(today.getFullYear(), today.getMonth(), 1);
}

function openDay(day) {
  if (!day.events.length) return;
  selectedDay.value = day;
}

function formatDay(value) {
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(value);
}

function formatTime(value) {
  return new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
</script>

<template>
  <section class="agenda-calendar" aria-label="Calendrier des evaluations">
    <header class="calendar-toolbar">
      <div>
        <span class="calendar-caption">Calendrier mensuel</span>
        <h3>{{ monthLabel }}</h3>
      </div>
      <div class="calendar-actions">
        <button class="icon-button" type="button" title="Mois precedent" @click="changeMonth(-1)">
          <ChevronLeft :size="18" />
        </button>
        <button class="calendar-today-button" type="button" @click="goToToday">Aujourd'hui</button>
        <button class="icon-button" type="button" title="Mois suivant" @click="changeMonth(1)">
          <ChevronRight :size="18" />
        </button>
      </div>
    </header>

    <div class="calendar-legend">
      <span><i class="legend-dot event-dot"></i> Evenement</span>
      <span><i class="legend-dot exam-dot"></i> Examen</span>
    </div>

    <div class="calendar-grid calendar-weekdays" aria-hidden="true">
      <span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
    </div>

    <div class="calendar-grid calendar-days">
      <button
        v-for="day in calendarDays"
        :key="day.key"
        type="button"
        class="calendar-day"
        :class="{
          muted: !day.isCurrentMonth,
          today: day.isToday,
          'has-event': day.events.length,
          'has-exam': day.hasExam,
        }"
        :disabled="!day.events.length"
        :aria-label="day.events.length ? `${day.events.length} evenement(s) le ${formatDay(day.date)}` : formatDay(day.date)"
        @click="openDay(day)"
      >
        <span class="calendar-day-number">{{ day.dayNumber }}</span>
        <span v-if="day.events.length" class="calendar-event-title">
          {{ day.events[0].title }}
        </span>
        <small v-if="day.events.length > 1">+{{ day.events.length - 1 }}</small>
      </button>
    </div>

    <p v-if="!items.length" class="calendar-empty">{{ emptyLabel }}</p>

    <div v-if="selectedDay" class="modal-backdrop" @click.self="selectedDay = null">
      <section class="admin-modal agenda-detail-modal">
        <div class="modal-header">
          <div>
            <span class="eyebrow">AGENDA</span>
            <h2>{{ formatDay(selectedDay.date) }}</h2>
          </div>
          <button class="icon-button" type="button" aria-label="Fermer" @click="selectedDay = null">
            <X :size="18" />
          </button>
        </div>

        <div class="agenda-detail-list">
          <article v-for="item in selectedDay.events" :key="item.id">
            <div class="agenda-detail-heading">
              <CalendarDays :size="18" />
              <strong>{{ item.title }}</strong>
              <span class="status-pill" :class="{ danger: isExam(item) }">
                {{ item.evaluation_type }}
              </span>
            </div>
            <p v-if="item.description">{{ item.description }}</p>
            <div class="agenda-detail-meta">
              <span><Clock3 :size="16" /> {{ formatTime(item.scheduled_at) }}</span>
              <span>{{ item.target_study_level }}</span>
            </div>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>
