<script setup>
import { reactive, ref } from "vue";
import { ArrowLeft, GraduationCap, Loader2, LockKeyhole, ShieldCheck, UserRoundCheck } from "lucide-vue-next";
import { isSupabaseConfigured, signInWithPassword } from "../services/supabase";

const emit = defineEmits(["authenticated", "back"]);

const loading = ref(false);
const message = ref("");

const form = reactive({
  email: "",
  password: ""
});

async function submitAuth() {
  if (!isSupabaseConfigured) {
    message.value = "Configure VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY dans frontend/.env";
    return;
  }

  loading.value = true;
  message.value = "";
  try {
    const data = await signInWithPassword(form.email, form.password);

    if (data.session) {
      emit("authenticated", data.session);
    }
  } catch (error) {
    message.value = error.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="auth-layout">
    <button class="auth-back-button" type="button" @click="emit('back')">
      <ArrowLeft :size="18" />
      <span>Retour à l'accueil</span>
    </button>

    <div class="auth-info">
      <h1>Acces securise par role</h1>

      <div class="role-cards">
        <article>
          <GraduationCap :size="22" />
          <strong>Etudiant</strong>
          <span>Consulter les examens publies.</span>
        </article>
        <article>
          <UserRoundCheck :size="22" />
          <strong>Enseignant</strong>
          <span>Téléverser les cours et valider les examens générés par l’IA </span>
        </article>
        <article>
          <ShieldCheck :size="22" />
          <strong>Administration</strong>
          <span>Suivre les utilisateurs et la gouvernance.</span>
        </article>
      </div>
    </div>

    <form class="auth-card" @submit.prevent="submitAuth">
      <div class="section-title">
        <LockKeyhole :size="19" />
        <h2>Connexion</h2>
      </div>

      <label>
        <span class="field-label">Email</span>
        <input v-model="form.email" class="input-control" type="email" required placeholder="email@ecole.ma" />
      </label>

      <label>
        <span class="field-label">Mot de passe</span>
        <input v-model="form.password" class="input-control" type="password" required minlength="6" />
      </label>

      <p v-if="message" class="error-message">{{ message }}</p>

      <button class="btn btn-primary btn-full" type="submit" :disabled="loading">
        <Loader2 v-if="loading" :size="18" class="spin" />
        <LockKeyhole v-else :size="18" />
        <span>Se connecter</span>
      </button>
    </form>
  </section>
</template>
