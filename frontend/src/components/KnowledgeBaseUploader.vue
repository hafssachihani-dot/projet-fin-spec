<script setup>
import { ref } from "vue";
import { FileUp, Loader2, Upload } from "lucide-vue-next";
import { createKnowledgeBase } from "../services/api";

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

function handleFiles(event) {
  files.value = Array.from(event.target.files || []);
}

async function uploadKnowledgeBase() {
  if (!name.value || !subject.value || files.value.length === 0) {
    message.value = "Ajoute un nom, une matiere et au moins un document.";
    return;
  }

  isUploading.value = true;
  message.value = "";
  try {
    const kb = await createKnowledgeBase({
      name: name.value,
      subject: subject.value,
      files: files.value,
      token: props.accessToken,
    });
    emit("created", kb);
    message.value = "Knowledge base creee.";
  } catch (error) {
    message.value = error.message;
  } finally {
    isUploading.value = false;
  }
}
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
      <input id="kb-files" type="file" multiple accept=".pdf,.txt,.md,.docx" @change="handleFiles" />
    </label>

    <button class="btn btn-secondary" type="button" :disabled="isUploading" @click="uploadKnowledgeBase">
      <Loader2 v-if="isUploading" :size="18" class="spin" />
      <Upload v-else :size="18" />
      <span>Creer la base</span>
    </button>

    <p v-if="message" class="helper-text">{{ message }}</p>
  </div>
</template>
