<script setup>
import { computed, reactive, ref } from "vue";
import { GraduationCap, Loader2, LockKeyhole, ShieldCheck, UserRoundCheck } from "lucide-vue-next";
import { isSupabaseConfigured, signInWithPassword, signUpWithRole } from "../services/supabase";

const emit = defineEmits(["authenticated"]);

const mode = ref("login");
const loading = ref(false);
const message = ref("");

const form = reactive({
  fullName: "",
  email: "",
  password: "",
  role: "teacher",
  studyLevel: "Licence 2"
});

const roleLabel = computed(() => {
  const labels = {
    student: "Etudiant",
    teacher: "Enseignant",
    admin: "Administration"
  };
  return labels[form.role];
});

async function submitAuth() {
  if (!isSupabaseConfigured) {
    message.value = "Configure VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY dans frontend/.env";
    return;
  }

  loading.value = true;
  message.value = "";
  try {
    const data =
      mode.value === "login"
        ? await signInWithPassword(form.email, form.password)
        : await signUpWithRole({
            email: form.email,
            password: form.password,
            fullName: form.fullName,
            role: form.role,
            studyLevel: form.studyLevel
          });

    if (data.session) {
      emit("authenticated", data.session);
    } else {
      message.value = "Compte cree. Verifie ton email si la confirmation est activee dans Supabase.";
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
    <div class="auth-info">
      <span class="eyebrow">Supabase Auth</span>
      <h1>Acces securise par role</h1>
      <p>
        Un seul projet, trois espaces: etudiant, enseignant et administration.
        Supabase gere l'identite, la table profiles garde le role.
      </p>

      <div class="role-cards">
        <article>
          <GraduationCap :size="22" />
          <strong>Etudiant</strong>
          <span>Consulter les examens publies.</span>
        </article>
        <article>
          <UserRoundCheck :size="22" />
          <strong>Enseignant</strong>
          <span>Uploader les cours et lancer Agentic RAG.</span>
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
        <h2>{{ mode === "login" ? "Connexion" : "Creation de compte" }}</h2>
        <span class="status-pill">{{ roleLabel }}</span>
      </div>

      <label v-if="mode === 'register'">
        <span class="field-label">Nom complet</span>
        <input v-model="form.fullName" class="input-control" required placeholder="Ex. Samira Loren" />
      </label>

      <label>
        <span class="field-label">Email</span>
        <input v-model="form.email" class="input-control" type="email" required placeholder="email@ecole.ma" />
      </label>

      <label>
        <span class="field-label">Mot de passe</span>
        <input v-model="form.password" class="input-control" type="password" required minlength="6" />
      </label>

      <label v-if="mode === 'register'">
        <span class="field-label">Role</span>
        <select v-model="form.role" class="input-control">
          <option value="student">Etudiant</option>
          <option value="teacher">Enseignant</option>
          <option value="admin">Administration</option>
        </select>
      </label>

      <label v-if="mode === 'register' && form.role === 'student'">
        <span class="field-label">Classe / niveau</span>
        <select v-model="form.studyLevel" class="input-control">
          <option>Licence 1</option>
          <option>Licence 2</option>
          <option>Licence 3</option>
          <option>Master 1</option>
          <option>Master 2</option>
        </select>
      </label>

      <p v-if="message" class="error-message">{{ message }}</p>

      <button class="btn btn-primary btn-full" type="submit" :disabled="loading">
        <Loader2 v-if="loading" :size="18" class="spin" />
        <LockKeyhole v-else :size="18" />
        <span>{{ mode === "login" ? "Se connecter" : "Creer le compte" }}</span>
      </button>

      <button
        class="link-button"
        type="button"
        @click="mode = mode === 'login' ? 'register' : 'login'"
      >
        {{ mode === "login" ? "Creer un nouveau compte" : "J'ai deja un compte" }}
      </button>
    </form>
  </section>
</template>
