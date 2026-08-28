<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"

import cdlLogo from "../../assets/cdl-logo.png"
import {
  ApiClientError,
  apiUrl,
  getProject,
  listProjectEvents,
  listProjects,
  projectEventsUrl,
  uploadProject,
} from "../../shared/api/projects"
import { formatDate, formatRelativeTime } from "../../shared/formatting/date"
import type {
  AuditProject,
  ProjectEvent as ProjectProgressEvent,
  ProjectStatus,
  UploadProjectInput,
} from "../../shared/types/projects"
import ProjectSetupWizard from "./ProjectSetupWizard.vue"

const projects = ref<AuditProject[]>([])
const selectedId = ref<string | null>(null)
const events = ref<ProjectProgressEvent[]>([])
const loading = ref(true)
const detailLoading = ref(false)
const refreshing = ref(false)
const uploadOpen = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const pageError = ref("")
const correlationId = ref<string | null>(null)

let eventSource: EventSource | null = null
let reconnectTimer: number | null = null
let refreshTimer: number | null = null
let selectionSequence = 0

const selectedProject = computed(
  () => projects.value.find((project) => project.project_id === selectedId.value) || null,
)

const completedCount = computed(
  () => projects.value.filter((project) => project.status === "COMPLETED").length,
)
const processingCount = computed(
  () => projects.value.filter((project) => ["UPLOADING", "PROCESSING"].includes(project.status)).length,
)
const failedCount = computed(
  () => projects.value.filter((project) => project.status === "FAILED").length,
)
const latestEventId = computed(() => events.value.at(-1)?.event_id || 0)
const progressPercent = computed(() => {
  const project = selectedProject.value
  if (project?.status === "COMPLETED") return 100
  const current = events.value.reduce(
    (latest, event) => (event.completed_steps >= latest.completed_steps ? event : latest),
    { completed_steps: 0, total_steps: 8 },
  )
  return Math.min(99, Math.round((current.completed_steps / Math.max(current.total_steps, 1)) * 100))
})

onMounted(async () => {
  await loadOverview()
  refreshTimer = window.setInterval(() => void refreshOverview(), 15_000)
})

onBeforeUnmount(() => {
  closeEventStream()
  if (refreshTimer !== null) window.clearInterval(refreshTimer)
})

async function loadOverview(): Promise<void> {
  loading.value = true
  clearError()
  try {
    projects.value = await listProjects()
    const firstProject = projects.value[0]
    if (firstProject) await selectProject(firstProject.project_id)
  } catch (error) {
    setError(error)
  } finally {
    loading.value = false
  }
}

async function refreshOverview(): Promise<void> {
  refreshing.value = true
  try {
    const fresh = await listProjects()
    projects.value = fresh
    const firstProject = fresh[0]
    if (!selectedId.value && firstProject) await selectProject(firstProject.project_id)
    if (selectedId.value && !fresh.some((project) => project.project_id === selectedId.value)) {
      selectedId.value = fresh[0]?.project_id || null
    }
  } catch (error) {
    setError(error)
  } finally {
    refreshing.value = false
  }
}

async function selectProject(projectId: string): Promise<void> {
  if (selectedId.value === projectId && events.value.length) return
  selectedId.value = projectId
  events.value = []
  detailLoading.value = true
  closeEventStream()
  const sequence = ++selectionSequence

  try {
    const [project, history] = await Promise.all([
      getProject(projectId),
      listProjectEvents(projectId),
    ])
    if (sequence !== selectionSequence) return
    upsertProject(project)
    events.value = history
    if (isActive(project.status)) openEventStream(projectId)
  } catch (error) {
    if (sequence === selectionSequence) setError(error)
  } finally {
    if (sequence === selectionSequence) detailLoading.value = false
  }
}

async function refreshSelectedProject(projectId: string): Promise<AuditProject | null> {
  try {
    const project = await getProject(projectId)
    if (selectedId.value !== projectId) return null
    upsertProject(project)
    return project
  } catch (error) {
    setError(error)
    return null
  }
}

function openEventStream(projectId: string): void {
  closeEventStream()
  const source = new EventSource(projectEventsUrl(projectId, latestEventId.value), { withCredentials: true })
  eventSource = source

  source.addEventListener("progress", (message) => {
    if (selectedId.value !== projectId) return
    const event = JSON.parse((message as MessageEvent<string>).data) as ProjectProgressEvent
    if (!events.value.some((item) => item.event_id === event.event_id)) {
      events.value.push(event)
      events.value.sort((left, right) => left.event_id - right.event_id)
    }
    const project = selectedProject.value
    if (project) {
      upsertProject({ ...project, current_activity: event.message, updated_at: event.occurred_at })
    }
  })

  source.addEventListener("end", () => {
    source.close()
    if (eventSource === source) eventSource = null
    void refreshSelectedProject(projectId)
    void refreshOverview()
  })

  source.onerror = () => {
    source.close()
    if (eventSource === source) eventSource = null
    void recoverEventStream(projectId)
  }
}

async function recoverEventStream(projectId: string): Promise<void> {
  const project = await refreshSelectedProject(projectId)
  if (!project || !isActive(project.status) || selectedId.value !== projectId) return
  reconnectTimer = window.setTimeout(() => openEventStream(projectId), 2_500)
}

function closeEventStream(): void {
  eventSource?.close()
  eventSource = null
  if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
  reconnectTimer = null
}

async function handleUpload(input: UploadProjectInput): Promise<void> {
  uploading.value = true
  uploadProgress.value = 0
  clearError()
  try {
    const project = await uploadProject(input, (percent) => {
      uploadProgress.value = percent
    })
    upsertProject(project)
    uploadOpen.value = false
    await selectProject(project.project_id)
  } catch (error) {
    setError(error)
  } finally {
    uploading.value = false
  }
}

function downloadProject(project: AuditProject): void {
  if (!project.output_download_url || !project.allowed_actions.includes("DOWNLOAD_OUTPUT")) return
  window.location.assign(apiUrl(project.output_download_url))
}

function upsertProject(project: AuditProject): void {
  const index = projects.value.findIndex((item) => item.project_id === project.project_id)
  if (index === -1) projects.value.unshift(project)
  else projects.value.splice(index, 1, project)
  projects.value.sort(
    (left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
  )
}

function isActive(status: ProjectStatus): boolean {
  return status === "UPLOADING" || status === "PROCESSING"
}

function statusLabel(status: ProjectStatus): string {
  return {
    UPLOADING: "Uploading",
    PROCESSING: "Processing",
    COMPLETED: "Completed",
    FAILED: "Failed",
    READY_FOR_DISCOVERY: "Ready for discovery",
    CANDIDATES_AVAILABLE: "Candidates available",
    OUTPUT_AVAILABLE: "Output available",
  }[status]
}

function sourceLabel(source: string): string {
  return source === "FILE_UPLOAD" ? "Local folder" : source.replaceAll("_", " ").toLowerCase()
}

function setError(error: unknown): void {
  if (error instanceof ApiClientError) {
    pageError.value = error.message
    correlationId.value = error.correlationId
  } else {
    pageError.value = error instanceof Error ? error.message : "Something went wrong. Please try again."
    correlationId.value = null
  }
}

function clearError(): void {
  pageError.value = ""
  correlationId.value = null
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand-lockup">
        <img :src="cdlLogo" alt="City Developments Limited" class="company-logo" />
        <span class="brand-divider" aria-hidden="true" />
        <div class="product-name">
          <strong>Audit Report</strong>
          <span>Workspace</span>
        </div>
      </div>
      <div class="topbar-actions">
        <span class="environment-pill"><i /> POC environment</span>
        <button class="button button-primary button-compact" type="button" @click="uploadOpen = true">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          New project
        </button>
      </div>
    </header>

    <main class="page-wrap">
      <section class="page-intro">
        <div>
          <span class="eyebrow">Internal audit operations</span>
          <h1>Project workspace</h1>
          <p>Upload audit evidence, follow the AI-assisted drafting process, and retrieve completed issue logs.</p>
        </div>
        <div class="summary-strip" aria-label="Project summary">
          <div><span>All projects</span><strong>{{ projects.length }}</strong></div>
          <div><span>In progress</span><strong class="orange">{{ processingCount }}</strong></div>
          <div><span>Completed</span><strong class="green">{{ completedCount }}</strong></div>
          <div><span>Needs attention</span><strong class="red">{{ failedCount }}</strong></div>
        </div>
      </section>

      <div v-if="pageError" class="error-banner" role="alert">
        <span class="error-icon"><svg viewBox="0 0 24 24"><path d="M12 8v5m0 3h.01" /><circle cx="12" cy="12" r="9" /></svg></span>
        <div><strong>We couldn't complete that request</strong><span>{{ pageError }}</span><small v-if="correlationId">Reference: {{ correlationId }}</small></div>
        <button type="button" aria-label="Dismiss" @click="clearError">×</button>
      </div>

      <section class="workspace-card">
        <aside class="project-list-panel">
          <div class="panel-heading">
            <div><h2>Projects</h2><span>{{ projects.length }} total</span></div>
            <button class="icon-button" type="button" :class="{ spinning: refreshing }" aria-label="Refresh projects" @click="refreshOverview">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5" /><path d="M18.5 16a8 8 0 1 1 .5-9l1 5" /></svg>
            </button>
          </div>

          <div v-if="loading" class="project-list-skeleton" aria-label="Loading projects">
            <div v-for="item in 4" :key="item" class="skeleton-row"><i /><span /><small /></div>
          </div>

          <div v-else-if="!projects.length" class="empty-list">
            <span class="empty-illustration"><svg viewBox="0 0 48 48"><path d="M8 15h13l4-5h15v28H8z" /><path d="M8 20h32M24 25v8m-4-4h8" /></svg></span>
            <h3>No audit projects yet</h3>
            <p>Upload your first project folder to begin.</p>
            <button class="text-action" type="button" @click="uploadOpen = true">Create a project →</button>
          </div>

          <div v-else class="project-list">
            <button
              v-for="project in projects"
              :key="project.project_id"
              class="project-row"
              :class="{ active: selectedId === project.project_id }"
              type="button"
              @click="selectProject(project.project_id)"
            >
              <span class="project-file-icon"><svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5M9 13h6m-6 4h6" /></svg></span>
              <span class="project-row-copy">
                <strong>{{ project.name }}</strong>
                <small>{{ project.current_activity || "Waiting for activity" }}</small>
                <span class="project-row-meta">
                  <i class="status-dot" :class="project.status.toLowerCase()" />
                  {{ statusLabel(project.status) }}
                  <b>·</b>
                  {{ formatRelativeTime(project.updated_at) }}
                </span>
              </span>
              <svg class="row-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>
            </button>
          </div>
        </aside>

        <article class="project-detail-panel" :class="{ 'no-project-selected': !selectedProject && !detailLoading }">
          <div v-if="detailLoading" class="detail-loading"><span class="large-spinner" /><p>Loading project details…</p></div>

          <template v-else-if="selectedProject">
            <div class="detail-header">
              <div class="detail-title">
                <span class="status-badge" :class="selectedProject.status.toLowerCase()">
                  <i />{{ statusLabel(selectedProject.status) }}
                </span>
                <h2>{{ selectedProject.name }}</h2>
                <div class="detail-subtitle">
                  <span><svg viewBox="0 0 24 24"><path d="M3 7h7l2 2h9v11H3z" /></svg>{{ sourceLabel(selectedProject.source_type) }}</span>
                  <span><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>Created {{ formatDate(selectedProject.created_at) }}</span>
                </div>
              </div>
              <button
                v-if="selectedProject.allowed_actions.includes('DOWNLOAD_OUTPUT')"
                class="button button-primary"
                type="button"
                @click="downloadProject(selectedProject)"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11m-4-4 4 4 4-4" /><path d="M5 20h14" /></svg>
                Download DOCX
              </button>
            </div>

            <div v-if="isActive(selectedProject.status)" class="processing-callout">
              <div class="processing-ring" :style="{ '--progress': progressPercent + '%' }"><span>{{ progressPercent }}%</span></div>
              <div><span class="eyebrow">Processing project</span><strong>{{ selectedProject.current_activity || "Preparing project…" }}</strong><p>You can leave this page. Processing continues securely in the background.</p></div>
            </div>

            <div v-else-if="selectedProject.status === 'COMPLETED'" class="success-callout">
              <span><svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg></span>
              <div><strong>Your issue log is ready</strong><p>The generated DOCX has been validated and stored separately from the raw upload.</p></div>
            </div>

            <div v-else-if="selectedProject.status === 'FAILED'" class="failure-callout">
              <span><svg viewBox="0 0 24 24"><path d="M12 8v5m0 3h.01" /><circle cx="12" cy="12" r="9" /></svg></span>
              <div><strong>Processing stopped</strong><p>{{ selectedProject.error || "The project could not be processed." }}</p><small>Upload the corrected folder as a new project to try again.</small></div>
            </div>

            <div class="detail-grid">
              <section class="activity-card">
                <div class="section-heading"><div><span class="eyebrow">Live activity</span><h3>Processing timeline</h3></div><span v-if="isActive(selectedProject.status)" class="live-indicator"><i /> Live</span></div>

                <div v-if="events.length" class="timeline">
                  <div v-for="(event, index) in events" :key="event.event_id" class="timeline-item" :class="{ current: index === events.length - 1 && isActive(selectedProject.status), warning: event.warning }">
                    <span class="timeline-marker">
                      <svg v-if="index < events.length - 1 || !isActive(selectedProject.status)" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
                      <i v-else />
                    </span>
                    <div><strong>{{ event.message }}</strong><span>{{ event.stage.replaceAll("_", " ") }} · {{ formatDate(event.occurred_at) }}</span></div>
                  </div>
                </div>
                <div v-else class="empty-activity"><span class="large-spinner" v-if="isActive(selectedProject.status)" /><p>{{ selectedProject.current_activity || "No activity events have been recorded." }}</p></div>
              </section>

              <aside class="project-facts">
                <div class="section-heading"><div><span class="eyebrow">Project data</span><h3>Details</h3></div></div>
                <dl>
                  <div><dt>Current status</dt><dd><span class="mini-status" :class="selectedProject.status.toLowerCase()">{{ statusLabel(selectedProject.status) }}</span></dd></div>
                  <div><dt>Report version</dt><dd>{{ selectedProject.version || "—" }}</dd></div>
                  <div><dt>Issues generated</dt><dd>{{ selectedProject.issue_count ?? "—" }}</dd></div>
                  <div><dt>Completed</dt><dd>{{ formatDate(selectedProject.completed_at) }}</dd></div>
                  <div><dt>Raw files retained until</dt><dd>{{ selectedProject.raw_deleted_at ? "Deleted" : formatDate(selectedProject.raw_expires_at) }}</dd></div>
                </dl>
                <div class="retention-note"><svg viewBox="0 0 24 24"><path d="M12 3 4 6v5c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10V6z" /><path d="m9 12 2 2 4-5" /></svg><p><strong>Secure retention</strong><span>Raw files are removed after the retention period. Generated reports remain available.</span></p></div>
              </aside>
            </div>
          </template>

          <div v-else class="empty-detail">
            <span class="empty-illustration large"><svg viewBox="0 0 48 48"><path d="M10 7h20l8 8v26H10z" /><path d="M30 7v9h9M17 24h14m-14 7h10" /></svg></span>
            <h2>Select a project</h2>
            <p>Choose a project from the list to view its status and processing timeline.</p>
          </div>
        </article>
      </section>

      <footer class="page-footer"><span>City Developments Limited · Internal Audit</span><span>AI-assisted drafting · Auditor review required</span></footer>
    </main>

    <ProjectSetupWizard
      :open="uploadOpen"
      :uploading="uploading"
      :progress="uploadProgress"
      :error="pageError"
      @close="uploadOpen = false"
      @submit="handleUpload"
    />
  </div>
</template>
