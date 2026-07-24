<script setup>
import { ref } from "vue";
import { FileUp } from "lucide-vue-next";
import { createKnowledgeBase } from "../services/api";
import { refreshCurrentSession } from "../services/supabase";

const emit = defineEmits(["created"]);

const props = defineProps({
  accessToken: {
    type: String,
    default: "",
  },
});

const name = ref("Droit des contrats L2");
const subject = ref("Droit des contrats");
const files = ref([]);
const isUploading = ref(false);
const message = ref("");
const fileInput = ref(null);

function handleFiles(event) {
  files.value = Array.from(event.target.files || []);
}

async function createFromSelectedFiles() {
  if (!name.value || !subject.value || files.value.length === 0) {
    message.value = "Ajoute un nom, une matiere et au moins un document.";
    throw new Error(message.value);
  }

  isUploading.value = true;
  message.value = "";
  try {
    const activeSession = await refreshCurrentSession();
    const token = activeSession?.access_token;
    if (!token) {
      message.value = "Session expiree. Reconnecte-toi puis reessaie.";
      throw new Error(message.value);
    }

    const kb = await createKnowledgeBase({
      name: name.value,
      subject: subject.value,
      files: files.value,
      token,
    });
    emit("created", kb);
    message.value = "Knowledge base creee.";
    files.value = [];
    if (fileInput.value) fileInput.value.value = "";
    return kb;
  } catch (error) {
    if (error.code === "AUTH_SESSION_EXPIRED") {
      message.value = "Ta session a expire. Reconnecte-toi puis reessaie.";
    } else {
      message.value = error.message;
    }
    throw new Error(message.value);
  } finally {
    isUploading.value = false;
  }
}

function hasSelectedFiles() {
  return files.value.length > 0;
}

defineExpose({ createFromSelectedFiles, hasSelectedFiles });
</script>

<template>
  <div class="uploader">
    <label class="field-label" for="kb-name">Nom</label>
    <input id="kb-name" v-model="name" class="input-control" />

    <label class="field-label" for="kb-subject">Matiere</label>
    <input id="kb-subject" v-model="subject" class="input-control" />

    <label class="upload-zone" for="kb-files">
      <FileUp :size="22" />
      <span>{{ files.length ? `${files.length} fichier(s) selectionne(s)` : "Importer PDF, DOCX, TXT" }}</span>
      <input
        id="kb-files"
        ref="fileInput"
        type="file"
        multiple
        accept=".pdf,.txt,.md,.docx"
        @change="handleFiles"
      />
    </label>

    <p class="helper-text">
      La base sera creee automatiquement lorsque tu genereras l'examen.
    </p>

    <p v-if="message" class="helper-text">{{ message }}</p>
  </div>
</template>
