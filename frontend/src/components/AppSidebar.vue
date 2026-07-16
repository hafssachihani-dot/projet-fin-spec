<script setup>
import { computed } from "vue";
import { GraduationCap } from "lucide-vue-next";

const props = defineProps({
  items: {
    type: Array,
    required: true,
  },
  activePage: {
    type: String,
    required: true,
  },
  displayName: {
    type: String,
    default: "",
  },
  displayRole: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["navigate", "expand"]);

const initials = computed(() => {
  const source = props.displayName || props.displayRole || "U";
  return source
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
});
</script>

<template>
  <aside class="app-sidebar" tabindex="0" @mouseenter="emit('expand', true)" @mouseleave="emit('expand', false)">
    <div class="brand-block">
      <div class="brand-icon">
        <GraduationCap :size="22" />
      </div>
      <div class="brand-copy">
        <strong>ExamFactory</strong>
        <span>Agentic RAG</span>
      </div>
    </div>

    <nav class="sidebar-nav" aria-label="Navigation principale">
      <button
        v-for="item in items"
        :key="item.key"
        class="nav-item"
        :class="{ active: activePage === item.key }"
        type="button"
        @click="emit('navigate', item.key)"
      >
        <component :is="item.icon" :size="18" />
        <span class="nav-label">{{ item.label }}</span>
        <span class="nav-tooltip">{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <div class="profile-avatar">{{ initials }}</div>
      <div class="profile-copy">
        <strong>{{ displayName }}</strong>
        <span>{{ displayRole }}</span>
      </div>
    </div>
  </aside>
</template>
