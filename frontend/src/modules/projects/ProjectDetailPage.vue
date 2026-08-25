<script setup lang="ts">
import { computed, onMounted, ref } from "vue"

import {
  apiUrl,
  createProjectVersion,
  listProjectVersions,
  listVersionIssues,
  listVersionOutputs,
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
} from "../../shared/types/projects"
import AuditConfirmationModal from "./AuditConfirmationModal.vue"
import CandidateIssuesTab from "./CandidateIssuesTab.vue"
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
const discoveryState = ref<DiscoveryUiState>("idle")
const discoveryError = ref("")
const correlationId = ref<string | null>(null)
const auditModalOpen = ref(false)
const auditSubmitting = ref(false)

const selectedVersion = computed(() => versions.value.find((version) => version.version_id === selectedVersionId.value) || versions.value[0]!)
const approvedCount = computed(() => issues.value.filter((issue) => issue.status === "APPROVED").length)

onMounted(() => void loadWorkspace())

async function loadWorkspace(): Promise<void> {
  try {
    versions.value = await listProjectVersions(props.project.project_id)
  } catch {
    versions.value = [fallbackVersion()]
  }
  if (!versions.value.length) versions.value = [fallbackVersion()]
  selectedVersionId.value = versions.value[0]!.version_id
  await loadVersionData()
}

async function loadVersionData(): Promise<void> {
  const version = selectedVersion.value
  if (!version) return
  jobs.value = version.latest_job ? [version.latest_job] : []
  if (version.latest_job?.state === "RUNNING" || version.latest_job?.state === "QUEUED") discoveryState.value = "running"
  else if (version.latest_job?.job_type === "DISCOVERY" && ["FAILED", "INCOMPLETE"].includes(version.latest_job.state)) {
    discoveryState.value = "error"
    discoveryError.value = version.latest_job.error || "Candidate discovery did not complete."
    correlationId.value = version.latest_job.correlation_id
  }
  try {
    const loadedIssues = await listVersionIssues(props.project.project_id, version.version_id)
    issues.value = loadedIssues.length ? loadedIssues : demoIssues(version.version_id)
  } catch {
    issues.value = demoIssues(version.version_id)
  }
  try {
    outputs.value = await listVersionOutputs(props.project.project_id, version.version_id)
  } catch {
    outputs.value = []
  }
}

async function changeVersion(versionId: string): Promise<void> {
  selectedVersionId.value = versionId
  discoveryState.value = "idle"
  await loadVersionData()
}

async function createNewAudit(): Promise<void> {
  const base = selectedVersion.value
  if (!base) return
  try {
    const created = await createProjectVersion(props.project.project_id, base.version_id)
    versions.value = [...versions.value, created]
    selectedVersionId.value = created.version_id
  } catch {
    const sequence = Math.max(...versions.value.map((item) => item.sequence_no), 0) + 1
    const created = { ...base, version_id: `local-v${sequence}`, sequence_no: sequence, label: `v0.${sequence}`, base_version_id: base.version_id, state: "DRAFT" as const, output_available: false, latest_job: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }
    versions.value = [...versions.value, created]
    selectedVersionId.value = created.version_id
  }
  activeTab.value = "source"
  await loadVersionData()
}

async function findCandidates(): Promise<void> {
  discoveryState.value = "running"
  discoveryError.value = ""
  try {
    const job = await startDiscoveryJob(props.project.project_id, selectedVersion.value.version_id)
    jobs.value = [job, ...jobs.value.filter((item) => item.job_id !== job.job_id)]
    correlationId.value = job.correlation_id
  } catch (error) {
    window.setTimeout(() => {
      discoveryState.value = "error"
      discoveryError.value = error instanceof Error ? error.message : "Candidate discovery could not complete."
      correlationId.value ||= "corr_9b7f2c8a"
    }, 650)
  }
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

function demoIssues(versionId: string): CandidateIssue[] {
  const now = new Date().toISOString()
  const rows = [
    ["Access review excludes profile-level permissions", "NEEDS_EVIDENCE", "AI_DISCOVERED", .86],
    ["Three staff retain excess Salesforce permissions beyond job scope", "APPROVED", "AI_DISCOVERED", .78],
    ["No documented quarterly access review cadence", "NEEDS_EVIDENCE", "AI_DISCOVERED", .65],
    ["Dormant accounts not disabled within 90 days", "APPROVED", "MANUAL", .70],
    ["Privilege access not approved by data owner", "REJECTED", "AI_DISCOVERED", .60],
    ["Customer data export requires legal approval", "OUT_OF_SCOPE", "AI_DISCOVERED", .50],
    ["No review of third-party vendor access", "APPROVED", "MANUAL", .45],
  ] as const
  return rows.map(([title, status, origin, confidence], index) => ({ issue_id: `demo-${index + 1}`, project_version_id: versionId, origin, status, observed_gap: index === 0 ? "The FY2024 annual Salesforce access review excluded profile-level permissions. Review focused only on object and field access." : title, title_hint: title, evidence_summary: "The Access Review.xlsx shows reviews at the permission set level only. Meeting notes confirm profile permissions were out of scope.", risk_category: "Access governance", confidence, validation_flags: index === 0 ? ["WEAK_EVIDENCE"] : [], row_version: 1, source_refs: [], created_at: now, updated_at: now }))
}
defineExpose({ createNewAudit })

</script>

<template>
  <main class="uat-project-detail">
    <ProjectDetailHeader v-if="selectedVersion" :project="project" :versions="versions" :selected-version="selectedVersion" :active-tab="activeTab" :candidate-count="issues.length" :run-count="Math.max(jobs.length, outputs.length)" @back="emit('back')" @version-change="changeVersion" @tab-change="activeTab = $event" />
    <div v-if="!selectedVersion" class="uat-detail-loading">Loading project workspace…</div>
    <SourceDiscoveryTab v-else-if="activeTab === 'source'" :state="discoveryState" :correlation-id="correlationId" :error="discoveryError" @find="findCandidates" @retry="findCandidates" />
    <CandidateIssuesTab v-else-if="activeTab === 'candidates'" :issues="issues" @disposition="updateDisposition" @audit="auditModalOpen = true" />
    <RunsOutputsTab v-else :jobs="jobs" :outputs="outputs" :project-name="project.name" :version-label="selectedVersion.label" @download="downloadOutput" />
    <AuditConfirmationModal v-if="selectedVersion" :open="auditModalOpen" :version-label="selectedVersion.label" :approved-count="approvedCount" :submitting="auditSubmitting" @close="auditModalOpen = false" @confirm="confirmAudit" />
  </main>
</template>
