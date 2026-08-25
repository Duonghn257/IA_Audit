<script setup lang="ts">
import type { AuditProject, ProjectVersion } from "../../shared/types/projects"

export type ProjectTab = "source" | "candidates" | "runs"

const props = defineProps<{
  project: AuditProject
  versions: ProjectVersion[]
  selectedVersion: ProjectVersion
  activeTab: ProjectTab
  candidateCount: number
  runCount: number
}>()

const emit = defineEmits<{
  back: []
  versionChange: [versionId: string]
  tabChange: [tab: ProjectTab]
}>()

function onVersionChange(event: Event): void {
  emit("versionChange", (event.target as HTMLSelectElement).value)
}

function stateLabel(state: ProjectVersion["state"]): string {
  return state.replaceAll("_", " ")
}
</script>

<template>
  <section class="uat-project-heading">
    <div class="uat-breadcrumb-line">
      <button class="uat-breadcrumb" type="button" @click="emit('back')">Projects</button>
      <span>/</span>
      <strong>{{ project.name }}</strong>
    </div>

    <div class="uat-project-title-row">
      <span class="uat-project-folder">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h7l2 2h9v11H3z" /></svg>
      </span>
      <div class="uat-project-title-copy">
        <h1>{{ project.name }}</h1>
        <div class="uat-version-line">
          <label>
            <span class="visually-hidden">Version</span>
            <select :value="selectedVersion.version_id" @change="onVersionChange">
              <option v-for="version in versions" :key="version.version_id" :value="version.version_id">
                Version: {{ version.label }}
              </option>
            </select>
          </label>
          <i />
          <span>Based on&nbsp; {{ selectedVersion.base_version_id ? versions.find((item) => item.version_id === selectedVersion.base_version_id)?.label || "—" : "—" }}</span>
          <i />
          <span class="uat-state-chip" :class="selectedVersion.state.toLowerCase()">
            {{ stateLabel(selectedVersion.state) }}
          </span>
          <i />
          <span>Output&nbsp; <b>{{ selectedVersion.output_available ? (selectedVersion.state === "STALE_OUTPUT" ? "STALE" : "CURRENT") : "No output" }}</b></span>
        </div>
      </div>
    </div>

    <nav class="uat-project-tabs" aria-label="Project workspace tabs">
      <button :class="{ active: props.activeTab === 'source' }" type="button" @click="emit('tabChange', 'source')">
        Source &amp; discovery
      </button>
      <button :class="{ active: props.activeTab === 'candidates' }" type="button" @click="emit('tabChange', 'candidates')">
        Candidate issues <span>{{ candidateCount }}</span>
      </button>
      <button :class="{ active: props.activeTab === 'runs' }" type="button" @click="emit('tabChange', 'runs')">
        Runs &amp; outputs <span>{{ runCount }}</span>
      </button>
    </nav>
  </section>
</template>
