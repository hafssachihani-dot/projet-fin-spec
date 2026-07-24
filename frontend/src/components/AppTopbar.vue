<script setup>
import { LogOut, RefreshCw, Search, UserPlus } from "lucide-vue-next";

defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: "",
  },
  displayRole: {
    type: String,
    default: "",
  },
  displayName: {
    type: String,
    default: "",
  },
  isAdmin: {
    type: Boolean,
    default: false,
  },
  isRefreshing: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["create-user", "refresh", "sign-out"]);
</script>

<template>
  <header class="topbar">
    <div>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </div>

    <div class="topbar-actions">
      <label class="search-box">
        <Search :size="17" />
        <input placeholder="Search" />
      </label>
      <span class="user-chip">{{ displayRole }} - {{ displayName }}</span>
      <button
        class="icon-button"
        type="button"
        title="Actualiser cette page"
        aria-label="Actualiser cette page"
        :disabled="isRefreshing"
        @click="emit('refresh')"
      >
        <RefreshCw :size="17" :class="{ 'spin-icon': isRefreshing }" />
      </button>
      <button
        v-if="isAdmin"
        class="icon-button"
        type="button"
        aria-label="Creer un utilisateur"
        @click="emit('create-user')"
      >
        <UserPlus :size="17" />
      </button>
      <button class="icon-button" type="button" aria-label="Se deconnecter" @click="emit('sign-out')">
        <LogOut :size="17" />
      </button>
    </div>
  </header>
</template>
