<script setup>
import { reactive, ref } from "vue";
import { Loader2, UserPlus } from "lucide-vue-next";
import { createManagedUser } from "../services/api";

const props = defineProps({
  accessToken: {
    type: String,
    required: true
  }
});

const emit = defineEmits(["close"]);

const form = reactive({
  full_name: "",
  email: "",
  password: "",
  role: "student",
  study_level: "Licence 2"
});

const loading = ref(false);
const message = ref("");
const createdUser = ref(null);

async function submitUser() {
  loading.value = true;
  message.value = "";
  createdUser.value = null;

  try {
    const result = await createManagedUser(props.accessToken, { ...form });
    createdUser.value = result.user;
    message.value = result.message;
    form.full_name = "";
    form.email = "";
    form.password = "";
    form.role = "student";
    form.study_level = "Licence 2";
  } catch (error) {
    message.value = error.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="admin-modal">
      <div class="modal-header">
        <div>
          <span class="eyebrow">Administration</span>
          <h2>Creer un compte</h2>
        </div>
        <button class="icon-button" type="button" aria-label="Fermer" @click="emit('close')">
          x
        </button>
      </div>

      <form class="modal-form" @submit.prevent="submitUser">
        <label>
          <span class="field-label">Nom complet</span>
          <input v-model="form.full_name" class="input-control" required placeholder="Ex. Ali Benali" />
        </label>

        <label>
          <span class="field-label">Email</span>
          <input v-model="form.email" class="input-control" type="email" required placeholder="utilisateur@ecole.ma" />
        </label>

        <label>
          <span class="field-label">Role</span>
          <select v-model="form.role" class="input-control">
            <option value="student">Etudiant</option>
            <option value="teacher">Enseignant</option>
          </select>
        </label>

        <label v-if="form.role === 'student'">
          <span class="field-label">Classe / niveau</span>
          <select v-model="form.study_level" class="input-control">
            <option>Licence 1</option>
            <option>Licence 2</option>
            <option>Licence 3</option>
            <option>Master 1</option>
            <option>Master 2</option>
          </select>
        </label>

        <label>
          <span class="field-label">Mot de passe initial</span>
          <input v-model="form.password" class="input-control" type="password" required minlength="6" />
        </label>

        <button class="btn btn-success btn-full" type="submit" :disabled="loading">
          <Loader2 v-if="loading" :size="18" class="spin" />
          <UserPlus v-else :size="18" />
          <span>Creer le compte</span>
        </button>
      </form>

      <p v-if="message" class="helper-text">{{ message }}</p>

      <div v-if="createdUser" class="created-box">
        <strong>Compte cree</strong>
        <span>{{ createdUser.full_name }} - {{ createdUser.email }} - {{ createdUser.role }}</span>
      </div>
    </section>
  </div>
</template>
