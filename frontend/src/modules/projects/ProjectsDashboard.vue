<script setup lang="ts">
import { computed } from "vue"

import { formatDate } from "../../shared/formatting/date"
import type { AuditProject } from "../../shared/types/projects"

const props = defineProps<{
  projects: AuditProject[]
  loading: boolean
}>()

defineEmits<{
  open: [project: AuditProject]
}>()

type DashboardStage = "ready" | "review" | "output" | "attention"

const stageCounts = computed(() => ({
  ready: props.projects.filter((project) => dashboardStage(project) === "ready").length,
  review: props.projects.filter((project) => dashboardStage(project) === "review").length,
  output: props.projects.filter((project) => dashboardStage(project) === "output").length,
  attention: props.projects.filter((project) => dashboardStage(project) === "attention").length,
}))

function dashboardStage(project: AuditProject): DashboardStage {
  if (project.status === "FAILED") return "attention"
  if (project.status === "COMPLETED") return "output"
  if (project.status === "PROCESSING") return "review"
  return "ready"
}

function stageLabel(project: AuditProject): string {
  return {
    ready: "Ready for discovery",
    review: "Needs review",
    output: "Output available",
    attention: "Needs attention",
  }[dashboardStage(project)]
}
</script>

<template>
  <main class="uat-dashboard">
    <section class="uat-dashboard-intro">
      <div>
        <span class="uat-eyebrow">Internal audit operations</span>
        <h1>Project workspace</h1>
        <p>Create audit projects, review AI candidates, and download versioned issue logs.</p>
      </div>
      <div class="uat-summary-cards">
        <article><span>Ready for discovery</span><strong class="green">{{ stageCounts.ready }}</strong></article>
        <article><span>Needs review</span><strong class="orange">{{ stageCounts.review }}</strong></article>
        <article><span>Output available</span><strong class="green">{{ stageCounts.output }}</strong></article>
        <article><span>Needs attention</span><strong class="red">{{ stageCounts.attention }}</strong></article>
      </div>
    </section>

    <section class="uat-project-table-card">
      <h2>Projects</h2>
      <div class="uat-project-table" role="table" aria-label="Audit projects">
        <div class="uat-project-table-head" role="row">
          <span role="columnheader">Project</span>
          <span role="columnheader">Current version</span>
          <span role="columnheader">Stage</span>
          <span role="columnheader">Updated</span>
          <span role="columnheader">Action</span>
        </div>
        <div v-if="loading" class="uat-table-empty">Loading projects…</div>
        <div v-else-if="!projects.length" class="uat-table-empty">No audit projects yet.</div>
        <template v-else>
          <button
            v-for="project in projects"
            :key="project.project_id"
            class="uat-project-table-row"
            type="button"
            role="row"
            @click="$emit('open', project)"
          >
            <span class="uat-table-project" role="cell">
              <i><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5M9 13h6m-6 4h6" /></svg></i>
              <span><strong>{{ project.name }}</strong><small>Created {{ formatDate(project.created_at) }}</small></span>
            </span>
            <strong role="cell">{{ project.version || "v0.1" }}</strong>
            <span role="cell"><b class="uat-stage-badge" :class="dashboardStage(project)"><i />{{ stageLabel(project) }}</b></span>
            <span role="cell">{{ formatDate(project.updated_at) }}</span>
            <span role="cell" class="uat-row-arrow"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg></span>
          </button>
        </template>
      </div>
    </section>
  </main>
</template>
