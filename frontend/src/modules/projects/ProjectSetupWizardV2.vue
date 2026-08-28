<script setup lang="ts">
import { computed, ref, watch } from "vue"
import PrimaryButton from "../../shared/ui/PrimaryButton.vue"

import {
  createUploadSession,
  discardUploadSession,
  promoteUploadSession,
  uploadSessionFiles,
  validateUploadSession,
} from "../../shared/api/projects"
import { formatBytes } from "../../shared/formatting/date"
import type { CreatedAuditProject, LogicalRole, UploadSession, UploadSessionFile } from "../../shared/types/projects"

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; created: [project: CreatedAuditProject] }>()

const folderInput = ref<HTMLInputElement | null>(null)
const step = ref<1 | 2>(1)
const projectName = ref("")
const files = ref<File[]>([])
const session = ref<UploadSession | null>(null)
const uploading = ref(false)
const validating = ref(false)
const creating = ref(false)
const progress = ref(0)
const uploadedFiles = ref(0)
const error = ref("")

const MAX_UPLOAD_BYTES = 100_000_000
const SUPPORTED_FILE = /\.(docx|pdf|xlsx)$/i
const REQUIRED_FOLDER = /(^|\/)(AWP|APM|Process SOP|Process Understanding)(\/|$)/
const CENTRAL_FOLDER = /(^|\/)(Guidelines|Samples|Output)(\/|$)|template/i

function relativePath(file: File): string {
  return file.webkitRelativePath || file.name
}

function isTemporaryFile(file: File): boolean {
  return /(^|\/)(~\$|\.~)/.test(relativePath(file))
}

const uploadFiles = computed(() => files.value.filter((file) => SUPPORTED_FILE.test(file.name) && !isTemporaryFile(file) && REQUIRED_FOLDER.test(relativePath(file))))
const ignoredFiles = computed(() => files.value.filter((file) => !uploadFiles.value.includes(file)))
const centralAssetFiles = computed(() => files.value.filter((file) => CENTRAL_FOLDER.test(relativePath(file))))
const totalBytes = computed(() => uploadFiles.value.reduce((total, file) => total + file.size, 0))
const folderName = computed(() => files.value[0]?.webkitRelativePath.split("/").filter(Boolean)[0] || "Select a folder")
const precheckPassed = computed(() => uploadFiles.value.length > 0 && uploadFiles.value.length <= 20 && totalBytes.value <= MAX_UPLOAD_BYTES)
const canContinue = computed(() => precheckPassed.value && progress.value === 100 && Boolean(session.value) && !uploading.value)
const canCreate = computed(() => Boolean(session.value?.allowed_actions.includes("CREATE_PROJECT")) && !creating.value)
const centralDuplicates = computed(() => centralAssetFiles.value.length > 0)
const validationReport = computed(() => session.value?.validation_report)
const blockingFiles = computed(() => validationReport.value?.errors.length || 0)
const warningCount = computed(() => (validationReport.value?.warnings.length || 0) + centralAssetFiles.value.length)
const roleCoverage = [["SCOPE", "AWP (Scope of work)"], ["RISK_CONTEXT", "APM (Risk context)"], ["EVIDENCE", "Evidence (Process understanding)"], ["CRITERIA", "Criteria (Process SOP)"]] as const
const roleGroups = computed(() => {
  const groups = new Map<string, UploadSessionFile[]>()
  for (const file of session.value?.files || []) {
    const pathParts = file.relative_path.split("/").filter(Boolean)
    const folder = pathParts.length > 2 ? pathParts[1]! : pathParts[0] || "Files"
    const group = groups.get(folder) || []
    group.push(file)
    groups.set(folder, group)
  }
  return [...groups.entries()]
})

watch(() => props.open, (open) => {
  if (open) reset()
})

function reset(): void {
  step.value = 1
  projectName.value = ""
  files.value = []
  session.value = null
  uploading.value = false
  validating.value = false
  creating.value = false
  progress.value = 0
  uploadedFiles.value = 0
  error.value = ""
  if (folderInput.value) folderInput.value.value = ""
}

function chooseFolder(): void {
  if (!uploading.value) folderInput.value?.click()
}

async function onFolderSelected(event: Event): Promise<void> {
  const selected = Array.from((event.target as HTMLInputElement).files || [])
  files.value = selected
  error.value = ""
  progress.value = 0
  uploadedFiles.value = 0
  if (!projectName.value && selected.length) projectName.value = folderName.value.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
  if (!precheckPassed.value) return
  uploading.value = true
  try {
    const created = await createUploadSession(uploadFiles.value)
    session.value = await uploadSessionFiles(created, uploadFiles.value, (percent, count) => {
      progress.value = percent
      uploadedFiles.value = count
    })
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Files could not be uploaded to secure staging."
  } finally {
    uploading.value = false
  }
}

async function continueToValidation(): Promise<void> {
  if (!canContinue.value || !session.value) return
  validating.value = true
  error.value = ""
  try {
    session.value = await validateUploadSession(session.value.session_id)
    step.value = 2
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Server validation could not complete."
  } finally {
    validating.value = false
  }
}

async function createProject(): Promise<void> {
  if (!canCreate.value || !session.value || !projectName.value.trim()) return
  creating.value = true
  error.value = ""
  try {
    const project = await promoteUploadSession(session.value.session_id, projectName.value.trim())
    emit("created", project)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Project could not be created."
  } finally {
    creating.value = false
  }
}

function close(): void {
  if (uploading.value || creating.value) return
  if (session.value && session.value.state !== "PROMOTED") void discardUploadSession(session.value.session_id)
  emit("close")
}

function roleLabel(role: LogicalRole | null): string {
  return role?.replaceAll("_", " ") || "CONTEXT"
}

function roleFound(role: Exclude<LogicalRole, "CONTEXT">): boolean {
  return (validationReport.value?.role_summary[role] || 0) > 0
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="uat-modal-backdrop uat-project-modal-backdrop" role="presentation" @mousedown.self="close">
      <section class="uat-project-modal" :class="{ validation: step === 2 }" role="dialog" aria-modal="true">
        <header class="uat-project-modal-header">
          <div><span class="uat-eyebrow">New audit project</span><h2>{{ step === 1 ? "Select & upload" : "Validate & create" }}</h2><p>{{ step === 1 ? "Choose the complete local audit folder." : "Server validation complete" }}</p></div>
          <ol><li :class="{ active: step === 1, done: step === 2 }"><b>{{ step === 2 ? "✓" : "1" }}</b><span>Select &amp; upload</span></li><i /><li :class="{ active: step === 2 }"><b>2</b><span>Validate &amp; create</span></li></ol>
          <button class="uat-icon-button" type="button" aria-label="Close" @click="close">×</button>
        </header>

        <template v-if="step === 1">
          <div class="uat-upload-body">
            <label class="uat-field-label" for="uat-project-name"><strong>Project name</strong><span>Defaulted from root folder</span></label>
            <input id="uat-project-name" v-model="projectName" class="uat-text-input" type="text" maxlength="255" />
            <input ref="folderInput" class="visually-hidden" type="file" webkitdirectory directory multiple @change="onFolderSelected" />
            <button class="uat-folder-picker" type="button" @click="chooseFolder"><span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h7l2 2h9v11H3z" /></svg></span><strong>{{ folderName }}</strong><small>{{ files.length ? `${uploadFiles.length} supported files • ${formatBytes(totalBytes)}` : "Choose the complete project folder" }}</small><u>{{ files.length ? "Choose a different folder" : "Select folder" }}</u></button>
            <section class="uat-precheck"><h3>Browser pre-check</h3><div :class="{ fail: !uploadFiles.length }"><i>{{ uploadFiles.length ? "✓" : "!" }}</i><span>Supported audit files:<br /><b>DOCX, PDF, XLSX</b></span></div><div :class="{ fail: uploadFiles.length > 20 }"><i>{{ uploadFiles.length > 20 ? "!" : "✓" }}</i><span>{{ uploadFiles.length }} of 20 supported files</span></div><div :class="{ fail: totalBytes > MAX_UPLOAD_BYTES }"><i>{{ totalBytes > MAX_UPLOAD_BYTES ? "!" : "✓" }}</i><span>{{ formatBytes(totalBytes) }} of 100 MB</span></div></section>
            <p v-if="ignoredFiles.length" class="uat-relative-note">ⓘ&nbsp;&nbsp; {{ ignoredFiles.length }} unsupported, temporary, or centrally managed file(s) will be ignored.</p>
            <section v-if="uploadFiles.length" class="uat-upload-progress"><div><strong>{{ uploading ? "Uploading to secure staging" : progress === 100 ? "Upload complete" : "Ready to upload" }}</strong><small>{{ uploadedFiles }} of {{ uploadFiles.length }} files • {{ formatBytes(totalBytes * progress / 100) }}</small></div><b>{{ progress }}%</b><progress :value="progress" max="100" /></section>
            <p class="uat-relative-note">♢&nbsp;&nbsp; Only relative paths are sent. Your local absolute path is never stored.</p>
            <p v-if="error" class="uat-inline-error">{{ error }}</p>
          </div>
          <footer class="uat-project-modal-footer"><button class="uat-button uat-button-secondary" type="button" @click="close">Cancel</button><PrimaryButton type="button" :disabled="!canContinue || validating" @click="continueToValidation">{{ validating ? "Validating…" : "Continue to validation" }} →</PrimaryButton></footer>
        </template>

        <template v-else>
          <div class="uat-validation-body">
            <section class="uat-validation-tree"><header><strong>Source folder</strong><span>▱&nbsp; {{ folderName }}</span></header><div v-for="[folder, group] in roleGroups" :key="folder" class="uat-validation-group"><h3>⌄&nbsp;&nbsp; ▱&nbsp; {{ folder }} <small>{{ group.length }} files</small></h3><div v-for="file in group" :key="file.file_id"><span>▤&nbsp; {{ file.relative_path.split('/').at(-1) }}</span><b :class="file.logical_role?.toLowerCase()">{{ roleLabel(file.logical_role) }}</b><em>●&nbsp; {{ file.readability_status === "READABLE" ? "Ready" : file.readability_status }}</em></div></div><footer>▤&nbsp;&nbsp; {{ session?.files.length || 0 }} files&nbsp; • &nbsp;{{ roleGroups.length }} folders</footer></section>
            <aside class="uat-validation-sidebar"><article class="uat-validation-summary"><h3>Validation summary</h3><div><span><strong class="green">{{ session?.files.length || 0 }}</strong>files</span><span><strong :class="blockingFiles ? 'orange' : 'green'">{{ blockingFiles }}</strong>blocking errors</span><span><strong class="orange">{{ warningCount }}</strong>warnings</span></div></article><article class="uat-role-coverage"><h3>Role coverage</h3><p v-for="role in roleCoverage" :key="role[0]"><span>▤&nbsp; {{ role[1] }}</span><b>{{ roleFound(role[0]) ? "Found ✓" : "Missing !" }}</b></p></article><article v-if="centralDuplicates" class="uat-central-warning"><strong>△&nbsp; Central asset duplicates detected</strong><p>{{ centralAssetFiles.length }} centrally managed file(s) were excluded and will not override central assets.</p></article><article v-if="canCreate" class="uat-can-create"><strong>♢&nbsp; Project can be created</strong><p>All required roles are present and validation checks passed.</p></article><article v-else class="uat-central-warning"><strong>!&nbsp; Project cannot be created</strong><p>{{ validationReport?.errors.map((item) => item.message).join(" ") || session?.action_reasons.CREATE_PROJECT }}</p></article><p class="uat-create-note">ⓘ&nbsp;&nbsp; Create project freezes the source and creates v0.1.<br />&nbsp;&nbsp;&nbsp;&nbsp; AI discovery will not start automatically.</p></aside>
          </div>
          <p v-if="error" class="uat-inline-error validation-error">{{ error }}</p>
          <footer class="uat-project-modal-footer validation-footer"><button class="uat-button uat-button-secondary" type="button" @click="step = 1">‹&nbsp; Back</button><span><i />{{ canCreate ? "Allowed by server validation" : session?.action_reasons.CREATE_PROJECT || "Create project is not allowed" }}</span><PrimaryButton type="button" :disabled="!canCreate" @click="createProject">{{ creating ? "Creating…" : "Create project" }} →</PrimaryButton></footer>
        </template>
      </section>
    </div>
  </Teleport>
</template>
