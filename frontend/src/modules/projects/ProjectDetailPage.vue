<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"

import {
  apiUrl,
  createProjectVersion,
  getJob,
  getProjectSourceTree,
  listProjectVersions,
  listVersionIssues,
  listVersionOutputs,
  retryDiscoveryJob,
  setIssueDisposition,
  startAuditJob,
  startDiscoveryJob,
} from "../../shared/api/projects"
import type {
  AuditJob,
  AuditProject,
  CandidateIssue,
  IssueStatus,
  OutputRevision,
  ProjectVersion,
  SourceTree,
} from "../../shared/types/projects"
import AuditConfirmationModal from "./AuditConfirmationModal.vue"
import CandidateIssuesTab from "./CandidateIssuesTab.vue"
import NewAuditVersionModal from "./NewAuditVersionModal.vue"
import ProjectDetailHeader, { type ProjectTab } from "./ProjectDetailHeader.vue"
import RunsOutputsTab from "./RunsOutputsTab.vue"
import SourceDiscoveryTab, { type DiscoveryUiState } from "./SourceDiscoveryTab.vue"

const props = defineProps<{ project: AuditProject }>()
const emit = defineEmits<{ back: []; error: [message: string] }>()

const activeTab = ref<ProjectTab>("source")
const versions = ref<ProjectVersion[]>([])
const selectedVersionId = ref("")
const issues = ref<CandidateIssue[]>([])
const outputs = ref<OutputRevision[]>([])
const jobs = ref<AuditJob[]>([])
const sourceTree = ref<SourceTree | null>(null)
const sourceLoading = ref(true)
const sourceError = ref("")
const discoveryState = ref<DiscoveryUiState>("idle")
const discoveryError = ref("")
const discoveryErrorTitle = ref("")
const correlationId = ref<string | null>(null)
const auditModalOpen = ref(false)
const auditSubmitting = ref(false)
const versionModalOpen = ref(false)
const versionSubmitting = ref(false)
const versionError = ref("")
const activeDiscoveryJobId = ref<string | null>(null)
let discoveryPollTimer: number | null = null

const selectedVersion = computed(() => versions.value.find((version) => version.version_id === selectedVersionId.value) || versions.value[0]!)
const approvedCount = computed(() => issues.value.filter((issue) => issue.status === "APPROVED").length)
const nextVersionLabel = computed(() => `v0.${Math.max(...versions.value.map((item) => item.sequence_no), 0) + 1}`)

onMounted(() => void loadWorkspace())
onBeforeUnmount(clearDiscoveryPolling)

async function loadWorkspace(): Promise<void> {
  void loadSourceTree()
  try {
    versions.value = await listProjectVersions(props.project.project_id)
  } catch {
    versions.value = [fallbackVersion()]
  }
  if (!versions.value.length) versions.value = [fallbackVersion()]
  selectedVersionId.value = versions.value[0]!.version_id
  await loadVersionData()
}

async function loadSourceTree(): Promise<void> {
  sourceLoading.value = true
  sourceError.value = ""
  try {
    sourceTree.value = await getProjectSourceTree(props.project.project_id)
  } catch (error) {
    sourceTree.value = null
    sourceError.value = error instanceof Error
      ? error.message
      : "Could not load the immutable project source."
  } finally {
    sourceLoading.value = false
  }
}

async function loadVersionData(): Promise<void> {
  const version = selectedVersion.value
  if (!version) return
  jobs.value = version.latest_job ? [version.latest_job] : []
  if (version.latest_job?.job_type === "DISCOVERY" && (version.latest_job.state === "RUNNING" || version.latest_job.state === "QUEUED")) {
    applyDiscoveryJob(version.latest_job)
  }
  else if (version.latest_job?.job_type === "DISCOVERY" && version.latest_job.state === "SUCCEEDED") discoveryState.value = "complete"
  else if (version.latest_job?.job_type === "DISCOVERY" && ["FAILED", "INCOMPLETE"].includes(version.latest_job.state)) {
    discoveryState.value = "error"
    discoveryErrorTitle.value = discoveryFailureTitle(version.latest_job.state)
    discoveryError.value = version.latest_job.error || "Candidate discovery did not complete."
    correlationId.value = version.latest_job.correlation_id
  }
  try {
    const loadedIssues = await listVersionIssues(props.project.project_id, version.version_id)
    issues.value = loadedIssues
  } catch {
    issues.value = []
  }
  try {
    outputs.value = await listVersionOutputs(props.project.project_id, version.version_id)
  } catch {
    outputs.value = []
  }
}

async function changeVersion(versionId: string): Promise<void> {
  clearDiscoveryPolling()
  selectedVersionId.value = versionId
  discoveryState.value = "idle"
  await loadVersionData()
}

function createNewAudit(): void {
  const base = selectedVersion.value
  if (!base) return
  if (!base.allowed_actions.includes("CREATE_VERSION")) {
    emit("error", "A new audit version cannot be created from the selected version.")
    return
  }
  versionError.value = ""
  versionModalOpen.value = true
}

async function confirmCreateVersion(baseVersionId: string): Promise<void> {
  const base = versions.value.find((version) => version.version_id === baseVersionId)
  if (!base || versionSubmitting.value) return
  versionSubmitting.value = true
  versionError.value = ""
  try {
    const created = await createProjectVersion(props.project.project_id, base.version_id)
    versions.value = [created, ...versions.value.filter((item) => item.version_id !== created.version_id)]
    selectedVersionId.value = created.version_id
    issues.value = []
    outputs.value = []
    jobs.value = []
    discoveryState.value = "idle"
    correlationId.value = null
    activeDiscoveryJobId.value = null
    versionModalOpen.value = false
    activeTab.value = "source"
  } catch (error) {
    versionError.value = error instanceof Error ? error.message : "Could not create the new audit version."
  } finally {
    versionSubmitting.value = false
  }
}

async function findCandidates(): Promise<void> {
  const version = selectedVersion.value
  if (!version?.allowed_actions.includes("RUN_DISCOVERY")) {
    discoveryState.value = "error"
    discoveryErrorTitle.value = "Discovery unavailable"
    discoveryError.value = "Discovery is not allowed for the selected version. Reload the project and try again."
    return
  }
  discoveryState.value = "running"
  discoveryError.value = ""
  discoveryErrorTitle.value = ""
  try {
    const job = await startDiscoveryJob(props.project.project_id, version.version_id)
    applyDiscoveryJob(job)
  } catch (error) {
    discoveryState.value = "error"
    discoveryErrorTitle.value = "Discovery could not start"
    discoveryError.value = error instanceof Error ? error.message : "Candidate discovery could not complete."
  }
}

async function retryCandidates(): Promise<void> {
  const jobId = activeDiscoveryJobId.value || jobs.value.find((job) => job.job_type === "DISCOVERY" && ["FAILED", "INCOMPLETE"].includes(job.state))?.job_id
  if (!jobId) {
    await findCandidates()
    return
  }
  discoveryState.value = "running"
  discoveryError.value = ""
  discoveryErrorTitle.value = ""
  try {
    applyDiscoveryJob(await retryDiscoveryJob(jobId))
  } catch (error) {
    discoveryState.value = "error"
    discoveryErrorTitle.value = "Discovery retry could not start"
    discoveryError.value = error instanceof Error ? error.message : "Candidate discovery retry could not start."
  }
}

function applyDiscoveryJob(job: AuditJob): void {
  jobs.value = [job, ...jobs.value.filter((item) => item.job_id !== job.job_id)]
  activeDiscoveryJobId.value = job.job_id
  correlationId.value = job.correlation_id
  clearDiscoveryPolling()
  if (["QUEUED", "RUNNING"].includes(job.state)) {
    discoveryState.value = "running"
    discoveryPollTimer = window.setTimeout(() => void pollDiscoveryJob(job.job_id), 1000)
  } else if (job.state === "SUCCEEDED") {
    discoveryState.value = "complete"
    void refreshAfterDiscovery()
  } else {
    discoveryState.value = "error"
    discoveryErrorTitle.value = discoveryFailureTitle(job.state)
    discoveryError.value = job.error || job.current_message || "Candidate discovery did not complete."
  }
}

async function pollDiscoveryJob(jobId: string): Promise<void> {
  try {
    applyDiscoveryJob(await getJob(jobId))
  } catch (error) {
    clearDiscoveryPolling()
    discoveryState.value = "error"
    discoveryErrorTitle.value = "Discovery status unavailable"
    discoveryError.value = error instanceof Error ? error.message : "Could not refresh discovery status."
  }
}

async function refreshAfterDiscovery(): Promise<void> {
  const versionId = selectedVersionId.value
  versions.value = await listProjectVersions(props.project.project_id)
  selectedVersionId.value = versionId
  issues.value = await listVersionIssues(props.project.project_id, versionId)
  activeTab.value = "candidates"
}

function clearDiscoveryPolling(): void {
  if (discoveryPollTimer !== null) window.clearTimeout(discoveryPollTimer)
  discoveryPollTimer = null
}

function discoveryFailureTitle(state: AuditJob["state"]): string {
  return state === "INCOMPLETE" ? "Discovery incomplete" : "Discovery failed"
}

async function updateDisposition(issue: CandidateIssue, status: IssueStatus): Promise<void> {
  const index = issues.value.findIndex((item) => item.issue_id === issue.issue_id)
  if (index < 0) return
  if (issue.issue_id.startsWith("demo-")) {
    issues.value.splice(index, 1, { ...issue, status, row_version: issue.row_version + 1 })
    return
  }
  try {
    const updated = await setIssueDisposition(props.project.project_id, selectedVersion.value.version_id, issue.issue_id, issue.row_version, status)
    issues.value.splice(index, 1, updated)
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Could not save the review decision.")
  }
}

async function confirmAudit(): Promise<void> {
  auditSubmitting.value = true
  try {
    const job = await startAuditJob(props.project.project_id, selectedVersion.value.version_id, selectedVersion.value.issue_revision)
    jobs.value = [job, ...jobs.value]
    auditModalOpen.value = false
    activeTab.value = "runs"
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Could not start the audit run.")
  } finally {
    auditSubmitting.value = false
  }
}

function downloadOutput(output: OutputRevision | null): void {
  const path = output?.download_url || props.project.output_download_url
  if (path) window.location.assign(apiUrl(path))
}

function fallbackVersion(): ProjectVersion {
  const now = new Date().toISOString()
  return { version_id: `fallback-${props.project.project_id}`, project_id: props.project.project_id, sequence_no: 1, label: props.project.version || "v0.1", base_version_id: null, state: props.project.output_available ? "DOCX_READY" : "DRAFT", issue_revision: 1, issue_counts: {}, latest_job: null, output_available: props.project.output_available, allowed_actions: ["CREATE_VERSION", "VIEW_ISSUES", "RUN_DISCOVERY", "RUN_AUDIT"], created_at: props.project.created_at, updated_at: now }
}

defineExpose({ createNewAudit })

</script>

<template>
  <main class="uat-project-detail">
    <ProjectDetailHeader v-if="selectedVersion" :project="project" :versions="versions" :selected-version="selectedVersion" :active-tab="activeTab" :candidate-count="issues.length" :run-count="Math.max(jobs.length, outputs.length)" @back="emit('back')" @new-audit="createNewAudit" @version-change="changeVersion" @tab-change="activeTab = $event" />
    <div v-if="!selectedVersion" class="uat-detail-loading">Loading project workspace…</div>
    <SourceDiscoveryTab v-else-if="activeTab === 'source'" :state="discoveryState" :source-tree="sourceTree" :source-loading="sourceLoading" :source-error="sourceError" :correlation-id="correlationId" :error="discoveryError" :error-title="discoveryErrorTitle" @find="findCandidates" @retry="retryCandidates" @reload-source="loadSourceTree" />
    <CandidateIssuesTab v-else-if="activeTab === 'candidates'" :issues="issues" @disposition="updateDisposition" @audit="auditModalOpen = true" />
    <RunsOutputsTab v-else :jobs="jobs" :outputs="outputs" :project-name="project.name" :version-label="selectedVersion.label" @download="downloadOutput" />
    <AuditConfirmationModal v-if="selectedVersion" :open="auditModalOpen" :version-label="selectedVersion.label" :approved-count="approvedCount" :submitting="auditSubmitting" @close="auditModalOpen = false" @confirm="confirmAudit" />
    <NewAuditVersionModal v-if="selectedVersion" :open="versionModalOpen" :project-name="project.name" :versions="versions" :initial-base-version-id="selectedVersion.version_id" :next-version-label="nextVersionLabel" :submitting="versionSubmitting" :error="versionError" @close="versionModalOpen = false" @confirm="confirmCreateVersion" />
  </main>
</template>
