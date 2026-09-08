<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { apiUrl, deleteCentralAsset, getCentralKnowledge, uploadGuideline, uploadTemplate } from "../../shared/api/projects"
import { formatBytes } from "../../shared/formatting/date"
import type { CentralAsset, CentralKnowledge } from "../../shared/types/projects"
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()
const knowledge = ref<CentralKnowledge | null>(null)
const loading = ref(false), uploadingTemplate = ref(false), uploadingGuidelines = ref(false)
const deletingId = ref(""), error = ref(""), notice = ref("")
const templateInput = ref<HTMLInputElement | null>(null)
const guidelineFolderInput = ref<HTMLInputElement | null>(null)
const guidelineFilesInput = ref<HTMLInputElement | null>(null)
const guidelineBytes = computed(() => knowledge.value?.guidelines.reduce((sum, item) => sum + item.size_bytes, 0) || 0)
watch(() => props.open, (open) => { if (open) void load() })
async function load(): Promise<void> {
  loading.value = true; error.value = ""
  try { knowledge.value = await getCentralKnowledge() }
  catch (cause) { error.value = message(cause, "Application configuration could not be loaded.") }
  finally { loading.value = false }
}
async function onTemplateSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement, file = input.files?.[0]; input.value = ""
  if (!file) return
  if (!/\.docx$/i.test(file.name)) { error.value = "Template must be a DOCX file."; return }
  uploadingTemplate.value = true; error.value = ""
  try { await uploadTemplate(file); notice.value = "Template updated successfully."; await load() }
  catch (cause) { error.value = message(cause, "Template could not be uploaded.") }
  finally { uploadingTemplate.value = false }
}
async function onGuidelinesSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement, selected = Array.from(input.files || []); input.value = ""
  const files = selected.filter((file) => /\.(docx|pdf|xlsx)$/i.test(file.name) && file.size > 0)
  if (files.length !== selected.length) { error.value = "Guidelines must be non-empty DOCX, PDF or XLSX files."; if (!files.length) return } else error.value = ""
  uploadingGuidelines.value = true; let uploaded = 0
  try {
    for (const file of files) { await uploadGuideline(file); uploaded += 1 }
    notice.value = `${uploaded} guideline file${uploaded === 1 ? "" : "s"} uploaded successfully.`; await load()
  } catch (cause) { error.value = `${uploaded} file(s) uploaded. ${message(cause, "The remaining guidelines could not be uploaded.")}`; await load() }
  finally { uploadingGuidelines.value = false }
}
async function remove(asset: CentralAsset): Promise<void> {
  if (!window.confirm(`Delete "${asset.filename}" from the current application configuration?`)) return
  deletingId.value = asset.asset_id; error.value = ""
  try { await deleteCentralAsset(asset.asset_id); notice.value = `${asset.filename} deleted.`; await load() }
  catch (cause) { error.value = message(cause, "The file could not be deleted.") }
  finally { deletingId.value = "" }
}
function downloadUrl(asset: CentralAsset): string { return apiUrl(asset.download_url) }
function message(cause: unknown, fallback: string): string { return cause instanceof Error ? cause.message : fallback }
</script>
<template>
  <Teleport to="body"><div v-if="open" class="uat-modal-backdrop uat-config-backdrop" @mousedown.self="$emit('close')">
    <section class="uat-config-modal" role="dialog" aria-modal="true" aria-labelledby="config-title">
      <header class="uat-config-header"><div><span class="uat-eyebrow">Application configuration</span><h2 id="config-title">Audit knowledge</h2><p>Manage the current template and guidelines used by every audit run.</p></div><div class="uat-config-readiness" :class="{ ready: knowledge?.ready_for_audit }"><i />{{ knowledge?.ready_for_audit ? "Ready for audit" : "Setup required" }}</div><button class="uat-icon-button" type="button" aria-label="Close" @click="$emit('close')">x</button></header>
      <div v-if="error" class="uat-config-alert error"><strong>Could not complete the request</strong><span>{{ error }}</span><button @click="error = ''">x</button></div>
      <div v-if="notice" class="uat-config-alert success"><span>{{ notice }}</span><button @click="notice = ''">x</button></div>
      <div v-if="loading && !knowledge" class="uat-config-loading"><span class="uat-source-spinner" />Loading configuration...</div>
      <div v-else class="uat-config-content">
        <article class="uat-config-card template"><header><span class="uat-config-card-icon">T</span><div><h3>Report template</h3><p>One DOCX file - uploading replaces the current template</p></div></header>
          <div v-if="knowledge?.template" class="uat-central-file featured"><span class="uat-file-type">DOCX</span><div><strong>{{ knowledge.template.filename }}</strong><small>{{ formatBytes(knowledge.template.size_bytes) }} - Updated {{ new Date(knowledge.template.updated_at).toLocaleString() }}</small></div><a :href="downloadUrl(knowledge.template)" download>View</a><button :disabled="deletingId === knowledge.template.asset_id" @click="remove(knowledge.template)">Delete</button></div>
          <div v-else class="uat-central-empty"><strong>No template uploaded</strong><span>Audit cannot run until a template is configured.</span></div>
          <input ref="templateInput" class="visually-hidden" type="file" accept=".docx" @change="onTemplateSelected" /><button class="uat-config-upload" type="button" :disabled="uploadingTemplate" @click="templateInput?.click()">{{ uploadingTemplate ? "Uploading..." : knowledge?.template ? "Replace template" : "Upload template" }}</button>
        </article>
        <article class="uat-config-card guidelines"><header><span class="uat-config-card-icon">G</span><div><h3>Guidelines</h3><p>Upload a folder containing DOCX, PDF and XLSX files</p></div><small>{{ knowledge?.guidelines.length || 0 }} files - {{ formatBytes(guidelineBytes) }}</small></header>
          <div class="uat-guideline-tree"><div class="uat-guideline-root"><b>Folder</b><strong>Guidelines</strong><small>{{ knowledge?.guidelines.length || 0 }} files</small></div><div v-if="!knowledge?.guidelines.length" class="uat-central-empty"><strong>No guidelines uploaded</strong><span>At least one guideline is required to run an audit.</span></div><div v-for="asset in knowledge?.guidelines" :key="asset.asset_id" class="uat-central-file"><span class="uat-file-type">{{ asset.filename.split('.').at(-1)?.toUpperCase() }}</span><div><strong>{{ asset.filename }}</strong><small>{{ formatBytes(asset.size_bytes) }} - {{ new Date(asset.updated_at).toLocaleString() }}</small></div><a :href="downloadUrl(asset)" download>View</a><button :disabled="deletingId === asset.asset_id" @click="remove(asset)">Delete</button></div></div>
          <input ref="guidelineFolderInput" class="visually-hidden" type="file" webkitdirectory directory multiple @change="onGuidelinesSelected" /><input ref="guidelineFilesInput" class="visually-hidden" type="file" multiple accept=".docx,.pdf,.xlsx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="onGuidelinesSelected" /><div class="uat-config-upload-actions"><button class="uat-config-upload secondary" type="button" :disabled="uploadingGuidelines" @click="guidelineFolderInput?.click()">{{ uploadingGuidelines ? "Uploading..." : "Upload folder" }}</button><button class="uat-config-upload" type="button" :disabled="uploadingGuidelines" @click="guidelineFilesInput?.click()">{{ uploadingGuidelines ? "Uploading..." : "Select DOCX, XLSX or PDF files" }}</button></div>
        </article>
      </div>
    </section>
  </div></Teleport>
</template>
