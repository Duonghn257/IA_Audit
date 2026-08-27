<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue"
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
  newAudit: []
  versionChange: [versionId: string]
  tabChange: [tab: ProjectTab]
}>()

const versionPicker = ref<HTMLElement | null>(null)
const versionMenuOpen = ref(false)

function selectVersion(versionId: string): void {
  versionMenuOpen.value = false
  if (versionId !== props.selectedVersion.version_id) emit("versionChange", versionId)
}

function closeVersionMenuOnOutside(event: PointerEvent): void {
  if (!versionPicker.value?.contains(event.target as Node)) versionMenuOpen.value = false
}

function closeVersionMenuOnEscape(event: KeyboardEvent): void {
  if (event.key === "Escape") versionMenuOpen.value = false
}

function baseLabel(version: ProjectVersion): string {
  if (!version.base_version_id) return "Initial version"
  const baseVersion = props.versions.find((item) => item.version_id === version.base_version_id)
  return `Based on ${baseVersion?.label || "previous version"}`
}

onMounted(() => {
  document.addEventListener("pointerdown", closeVersionMenuOnOutside)
  window.addEventListener("keydown", closeVersionMenuOnEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", closeVersionMenuOnOutside)
  window.removeEventListener("keydown", closeVersionMenuOnEscape)
})

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
          <div ref="versionPicker" class="uat-version-picker">
            <button class="uat-version-select" :class="{ open: versionMenuOpen }" type="button" aria-haspopup="listbox" :aria-expanded="versionMenuOpen" aria-controls="audit-version-listbox" @click="versionMenuOpen = !versionMenuOpen">
              <span class="uat-version-select-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="m12 3 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4M4 17l8 4 8-4" /></svg>
              </span>
              <span class="uat-version-select-control"><small>Current version</small><strong>{{ selectedVersion.label }}</strong></span>
              <svg class="uat-version-select-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5" /></svg>
            </button>
            <Transition name="uat-version-menu">
              <div v-if="versionMenuOpen" id="audit-version-listbox" class="uat-version-menu" role="listbox" aria-label="Audit versions">
                <!-- <div class="uat-version-menu-heading"><span>Audit versions</span><small>{{ versions.length }} total</small></div> -->
                <button v-for="version in versions" :key="version.version_id" class="uat-version-option" :class="{ selected: version.version_id === selectedVersion.version_id }" type="button" role="option" :aria-selected="version.version_id === selectedVersion.version_id" @click="selectVersion(version.version_id)">
                  <span class="uat-version-option-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m12 3 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4M4 17l8 4 8-4" /></svg></span>
                  <span class="uat-version-option-copy"><strong>{{ version.label }}</strong><small>{{ baseLabel(version) }}</small></span>
                  <svg v-if="version.version_id === selectedVersion.version_id" class="uat-version-option-check" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>
                </button>
              </div>
            </Transition>
          </div>
          <i />
          <span class="uat-version-meta"><small>Based on</small><strong>{{ selectedVersion.base_version_id ? versions.find((item) => item.version_id === selectedVersion.base_version_id)?.label || "—" : "—" }}</strong></span>
          <i />
          <span class="uat-state-chip" :class="selectedVersion.state.toLowerCase()">
            {{ stateLabel(selectedVersion.state) }}
          </span>
          <i />
          <span class="uat-version-meta"><small>Output</small><strong>{{ selectedVersion.output_available ? (selectedVersion.state === "STALE_OUTPUT" ? "STALE" : "CURRENT") : "No output" }}</strong></span>
        </div>
      </div>
      <button class="uat-button uat-button-primary uat-project-new-audit" type="button" @click="emit('newAudit')">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        New audit
      </button>
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
