<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"

import { getProject, listProjects } from "../../shared/api/projects"
import type { AuthSession } from "../../shared/auth/auth-api"
import type { AuditProject, CreatedAuditProject } from "../../shared/types/projects"
import ProjectDetailPage from "./ProjectDetailPage.vue"
import ProjectSetupWizardV2 from "./ProjectSetupWizardV2.vue"
import ProjectsDashboard from "./ProjectsDashboard.vue"
import WorkspaceHeader from "./WorkspaceHeader.vue"

defineProps<{ authSession: AuthSession; loggingOut?: boolean }>()
defineEmits<{ logout: [] }>()

const projects = ref<AuditProject[]>([])
const selectedProject = ref<AuditProject | null>(null)
const loading = ref(true)
const uploadOpen = ref(false)
const pageError = ref("")
const detailRef = ref<InstanceType<typeof ProjectDetailPage> | null>(null)

const activeProjectJobs = computed(() => selectedProject.value && ["UPLOADING", "PROCESSING"].includes(selectedProject.value.status) ? 1 : 0)

onMounted(async () => {
  window.addEventListener("popstate", syncRoute)
  await loadProjects()
  syncRoute()
})

onBeforeUnmount(() => window.removeEventListener("popstate", syncRoute))

async function loadProjects(): Promise<void> {
  loading.value = true
  try {
    projects.value = await listProjects()
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : "Could not load audit projects."
  } finally {
    loading.value = false
  }
}

async function openProject(project: AuditProject, updateHistory = true): Promise<void> {
  pageError.value = ""
  try {
    selectedProject.value = await getProject(project.project_id)
  } catch {
    selectedProject.value = project
  }
  if (updateHistory) window.history.pushState({}, "", `/projects/${encodeURIComponent(project.project_id)}`)
  window.scrollTo({ top: 0, behavior: "smooth" })
}

function backToProjects(updateHistory = true): void {
  selectedProject.value = null
  if (updateHistory) window.history.pushState({}, "", "/projects")
}

function syncRoute(): void {
  if (window.location.pathname === "/") window.history.replaceState({}, "", "/projects")
  const match = window.location.pathname.match(/^\/projects\/([^/]+)$/)
  if (!match) {
    selectedProject.value = null
    return
  }
  const projectId = decodeURIComponent(match[1]!)
  const project = projects.value.find((item) => item.project_id === projectId)
  if (project) void openProject(project, false)
}

function handlePrimaryAction(): void {
  if (selectedProject.value) detailRef.value?.createNewAudit()
  else uploadOpen.value = true
}

function handleCreated(result: CreatedAuditProject): void {
  const project: AuditProject = {
    project_id: result.project_id,
    name: result.name,
    source_type: "FILE_UPLOAD",
    status: result.state,
    current_activity: "Ready for discovery",
    allowed_actions: ["VIEW_STATUS"],
    created_at: result.created_at,
    updated_at: result.updated_at,
    started_at: null,
    completed_at: null,
    output_available: false,
    output_download_url: null,
    version: result.version.label,
    issue_count: 0,
    error: null,
    raw_expires_at: null,
    raw_deleted_at: null,
  }
  projects.value = [project, ...projects.value.filter((item) => item.project_id !== project.project_id)]
  uploadOpen.value = false
  void openProject(project)
}
</script>

<template>
  <div class="uat-app-shell">
    <WorkspaceHeader :running-jobs="activeProjectJobs" :primary-label="selectedProject ? 'New audit' : 'New project'" :user="authSession.user" :logging-out="loggingOut" @primary="handlePrimaryAction" @logout="$emit('logout')" />
    <div v-if="pageError" class="uat-page-error" role="alert"><strong>We couldn't complete that request</strong><span>{{ pageError }}</span><button type="button" @click="pageError = ''">×</button></div>
    <ProjectDetailPage v-if="selectedProject" ref="detailRef" :project="selectedProject" @back="backToProjects" @error="pageError = $event" />
    <ProjectsDashboard v-else :projects="projects" :loading="loading" @open="openProject" />
    <ProjectSetupWizardV2 :open="uploadOpen" @close="uploadOpen = false" @created="handleCreated" />
  </div>
</template>
