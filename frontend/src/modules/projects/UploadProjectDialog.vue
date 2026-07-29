<script setup lang="ts">
import { computed, ref, watch } from "vue"

import { formatBytes } from "../../shared/formatting/date"
import type { UploadProjectInput } from "../../shared/types/projects"

const props = defineProps<{
  open: boolean
  uploading: boolean
  progress: number
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: UploadProjectInput]
}>()

const input = ref<HTMLInputElement | null>(null)
const projectName = ref("")
const files = ref<File[]>([])
const validationMessage = ref("")

const folderName = computed(() => {
  const firstPath = files.value[0]?.webkitRelativePath
  return firstPath?.split("/").filter(Boolean)[0] || "Selected folder"
})

const totalBytes = computed(() => files.value.reduce((total, file) => total + file.size, 0))

const hasRootIssuesFile = computed(() =>
  files.value.some((file) => {
    if (file.name !== "sample_issues.json") return false
    const parts = (file.webkitRelativePath || file.name).split("/").filter(Boolean)
    return parts.length <= 2
  }),
)

const canSubmit = computed(
  () => files.value.length > 0 && hasRootIssuesFile.value && !props.uploading,
)

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    projectName.value = ""
    files.value = []
    validationMessage.value = ""
    if (input.value) input.value.value = ""
  },
)

function chooseFolder(): void {
  if (!props.uploading) input.value?.click()
}

function onFolderSelected(event: Event): void {
  const target = event.target as HTMLInputElement
  files.value = Array.from(target.files || [])
  validationMessage.value = ""

  if (!files.value.length) return
  if (!projectName.value.trim()) projectName.value = folderName.value.replace(/[_-]+/g, " ")
  if (!hasRootIssuesFile.value) {
    validationMessage.value = "This POC requires sample_issues.json at the root of the selected folder."
  }
}

function submit(): void {
  if (!files.value.length) {
    validationMessage.value = "Choose a project folder first."
    return
  }
  if (!hasRootIssuesFile.value) {
    validationMessage.value = "Add sample_issues.json at the root of the project folder before uploading."
    return
  }
  emit("submit", { name: projectName.value, files: files.value })
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" role="presentation" @mousedown.self="!uploading && emit('close')">
      <section
        class="upload-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-title"
      >
        <div class="dialog-header">
          <div>
            <span class="eyebrow">New audit project</span>
            <h2 id="upload-title">Upload project folder</h2>
            <p>Select the complete local audit folder. Its structure is preserved securely.</p>
          </div>
          <button class="icon-button" type="button" :disabled="uploading" aria-label="Close" @click="emit('close')">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
          </button>
        </div>

        <div class="dialog-body">
          <label class="field-label" for="project-name">Project name <span>Optional</span></label>
          <input
            id="project-name"
            v-model="projectName"
            class="text-input"
            type="text"
            maxlength="255"
            placeholder="e.g. Lumina Grand PDPA Audit"
            :disabled="uploading"
          />

          <input
            ref="input"
            class="visually-hidden"
            type="file"
            webkitdirectory
            directory
            multiple
            :disabled="uploading"
            @change="onFolderSelected"
          />

          <button
            class="folder-dropzone"
            :class="{ selected: files.length > 0 }"
            type="button"
            :disabled="uploading"
            @click="chooseFolder"
          >
            <span class="folder-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M3.5 7.5h6l2-2h9a1.5 1.5 0 0 1 1.5 1.5v11.5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 1.5-2Z" /><path d="M12 11v6m-3-3 3-3 3 3" /></svg>
            </span>
            <template v-if="files.length">
              <strong>{{ folderName }}</strong>
              <span>{{ files.length }} files · {{ formatBytes(totalBytes) }}</span>
              <small>Choose a different folder</small>
            </template>
            <template v-else>
              <strong>Choose a folder</strong>
              <span>Select the complete folder from your computer</span>
              <small>Maximum 500 files · 1 GB total</small>
            </template>
          </button>

          <div class="requirement" :class="{ valid: hasRootIssuesFile && files.length }">
            <span class="requirement-mark" aria-hidden="true">
              <svg v-if="hasRootIssuesFile && files.length" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
              <svg v-else viewBox="0 0 24 24"><path d="M12 8v5m0 3h.01" /><circle cx="12" cy="12" r="9" /></svg>
            </span>
            <div>
              <strong>Auditor input required</strong>
              <span>sample_issues.json must be at the folder root.</span>
            </div>
          </div>

          <p v-if="validationMessage" class="form-error" role="alert">{{ validationMessage }}</p>

          <div v-if="uploading" class="upload-progress" aria-live="polite">
            <div class="progress-copy"><span>Uploading securely…</span><strong>{{ progress }}%</strong></div>
            <div class="progress-track"><span :style="{ width: `${progress}%` }" /></div>
            <small>Keep this window open until processing begins.</small>
          </div>
        </div>

        <div class="dialog-footer">
          <button class="button button-secondary" type="button" :disabled="uploading" @click="emit('close')">Cancel</button>
          <button class="button button-primary" type="button" :disabled="!canSubmit" @click="submit">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m-5-5 5 5 5-5" /><path d="M5 20h14" /></svg>
            {{ uploading ? "Uploading…" : "Upload & process" }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>
