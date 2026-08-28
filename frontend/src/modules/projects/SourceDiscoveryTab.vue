<script setup lang="ts">
import { ref } from "vue"
import PrimaryButton from "../../shared/ui/PrimaryButton.vue"

import type { LogicalRole, SourceFolder, SourceTree } from "../../shared/types/projects"

export type DiscoveryUiState = "idle" | "running" | "error" | "complete"

defineProps<{
  state: DiscoveryUiState
  sourceTree: SourceTree | null
  sourceLoading: boolean
  sourceError?: string | null
  correlationId?: string | null
  error?: string | null
  errorTitle?: string | null
}>()

defineEmits<{
  find: []
  retry: []
  reloadSource: []
}>()

const expandedFolders = ref<Set<string>>(new Set())
const showCoverage = false

function folderKey(folder: SourceFolder): string {
  return `${folder.logical_role}:${folder.name}`
}

function folderDomId(folder: SourceFolder): string {
  return `source-folder-${folderKey(folder).replace(/[^a-zA-Z0-9_-]/g, "-")}`
}

function isExpanded(folder: SourceFolder): boolean {
  return expandedFolders.value.has(folderKey(folder))
}

function toggleFolder(folder: SourceFolder): void {
  const next = new Set(expandedFolders.value)
  const key = folderKey(folder)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedFolders.value = next
}

function beforePanelEnter(element: Element): void {
  const panel = element as HTMLElement
  panel.style.height = "0"
  panel.style.opacity = "0"
  panel.style.overflow = "hidden"
}

function panelEnter(element: Element): void {
  const panel = element as HTMLElement
  panel.style.height = `${panel.scrollHeight}px`
  panel.style.opacity = "1"
}

function afterPanelEnter(element: Element): void {
  const panel = element as HTMLElement
  panel.style.height = "auto"
  panel.style.overflow = ""
}

function beforePanelLeave(element: Element): void {
  const panel = element as HTMLElement
  panel.style.height = `${panel.scrollHeight}px`
  panel.style.opacity = "1"
  panel.style.overflow = "hidden"
  void panel.offsetHeight
}

function panelLeave(element: Element): void {
  const panel = element as HTMLElement
  panel.style.height = "0"
  panel.style.opacity = "0"
}

function roleLabel(role: LogicalRole): string {
  return role.replaceAll("_", " ")
}

function roleTone(role: LogicalRole): string {
  return {
    SCOPE: "scope",
    RISK_CONTEXT: "risk",
    EVIDENCE: "evidence",
    CRITERIA: "criteria",
    CONTEXT: "context",
  }[role]
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <section class="uat-source-tab">
    <article v-if="state === 'idle'" class="uat-find-card">
      <div>
        <span class="uat-find-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4M8 11h6m-3-3v6" /></svg></span>
        <div><h2>Find candidate issues</h2><p>Analyse the immutable source and build evidence-backed candidates for this version.</p></div>
      </div>
      <PrimaryButton type="button" @click="$emit('find')">Find candidates</PrimaryButton>
    </article>

    <article v-else-if="state === 'running'" class="uat-discovery-progress">
      <header class="uat-discovery-progress-header">
        <h2>Finding candidates</h2>
        <div><span>Job continues if you leave this page.</span><i /><span>Correlation ID:&nbsp; {{ correlationId || "—" }}</span></div>
      </header>
      <div class="uat-progress-steps">
        <div class="done"><b>✓</b><span><strong>Queued</strong><small>Completed</small></span></div><i />
        <div class="done"><b>✓</b><span><strong>Parsing</strong><small>Completed</small></span></div><i />
        <div class="active"><b>↻</b><span><strong>Discovering</strong><small>62%</small></span></div><i class="pending" />
        <div><b>4</b><span><strong>Validating</strong><small>Pending</small></span></div>
      </div>
    </article>

    <article v-else-if="state === 'error'" class="uat-discovery-error">
      <span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8v5m0 3h.01" /><path d="M12 3 2 21h20z" /></svg></span>
      <div><h2>{{ errorTitle || "Discovery could not complete" }}</h2><p>{{ error || "This may affect the accuracy of candidate discovery." }}</p><small v-if="correlationId">Correlation ID: {{ correlationId }}</small></div>
      <button class="uat-button uat-button-secondary" type="button">View error</button>
      <PrimaryButton type="button" @click="$emit('retry')">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5" /><path d="M18.5 16a8 8 0 1 1 .5-9l1 5" /></svg>
        Retry
      </PrimaryButton>
    </article>

    <div class="uat-source-grid" :class="{ 'source-only': !showCoverage }">
      <article class="uat-source-tree-card">
        <header>
          <h2>Immutable source</h2>
          <span v-if="sourceTree">{{ sourceTree.file_count }} files · {{ formatBytes(sourceTree.total_size_bytes) }}</span>
        </header>
        <div v-if="sourceLoading" class="uat-source-message"><span class="uat-source-spinner" />Loading source…</div>
        <div v-else-if="sourceError" class="uat-source-message uat-source-message-error">
          <span>{{ sourceError }}</span>
          <button type="button" @click="$emit('reloadSource')">Retry</button>
        </div>
        <div v-else-if="!sourceTree?.folders.length" class="uat-source-message">No source documents are available.</div>
        <template v-else>
          <div v-for="folder in sourceTree.folders" :key="folderKey(folder)" class="uat-source-folder">
            <button type="button" class="uat-source-row" :class="{ 'is-active': isExpanded(folder) }" :aria-expanded="isExpanded(folder)" :aria-controls="folderDomId(folder)" @click="toggleFolder(folder)">
              <span
                class="uat-source-chevron"
                :style="{ transform: isExpanded(folder) ? 'rotate(90deg)' : 'rotate(0deg)' }"
                aria-hidden="true"
              >
                <svg viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" /></svg>
              </span>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h7l2 2h9v11H3z" /></svg>
              <strong>{{ folder.name }}</strong>
              <small>{{ folder.file_count }} {{ folder.file_count === 1 ? "file" : "files" }}</small>
              <b :class="roleTone(folder.logical_role)">{{ roleLabel(folder.logical_role) }}</b>
            </button>
            <Transition
              name="source-folder-collapse"
              @before-enter="beforePanelEnter"
              @enter="panelEnter"
              @after-enter="afterPanelEnter"
              @before-leave="beforePanelLeave"
              @leave="panelLeave"
            >
              <div v-if="isExpanded(folder)" :id="folderDomId(folder)" class="uat-source-files-collapse">
                <div class="uat-source-files">
                  <div v-for="file in folder.files" :key="file.document_id" class="uat-source-file" :title="file.relative_path">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 2h8l4 4v16H6z" /><path d="M14 2v5h5" /></svg>
                    <div><strong>{{ file.name }}</strong><small>{{ formatBytes(file.size_bytes) }}</small></div>
                    <span class="uat-source-file-status" :class="file.parse_status.toLowerCase()">{{ file.parse_status.replaceAll("_", " ") }}</span>
                  </div>
                </div>
              </div>
            </Transition>
          </div>
        </template>
        <footer v-if="sourceTree"><span>{{ sourceTree.folder_count }} folders · Snapshot {{ sourceTree.status.toLowerCase() }}</span></footer>
      </article>

      <div v-if="showCoverage" class="uat-coverage-column">
        <div class="uat-coverage-stats">
          <article><span>Covered</span><strong class="green">8</strong><small>controls</small></article>
          <article><span>Candidate found</span><strong class="orange">5</strong><small>controls</small></article>
          <article><span>Missing evidence</span><strong class="red">2</strong><small>controls</small></article>
          <article><span>Incomplete parsing</span><strong class="orange">1</strong><small>control</small></article>
        </div>
        <article class="uat-coverage-card">
          <header><h2>Coverage by scope &amp; control</h2><button class="uat-button uat-button-secondary uat-button-small" type="button">View details ›</button></header>
          <div class="uat-coverage-head"><span>Status</span><span>Controls</span></div>
          <div><span><i class="green" />Covered</span><strong>8 (44%)</strong></div>
          <div><span><i class="orange" />Candidate found</span><strong>5 (28%)</strong></div>
          <div><span><i class="red" />Missing evidence</span><strong>2 (11%)</strong></div>
          <div><span><i class="orange minus" />Incomplete</span><strong>1 (6%)</strong></div>
          <div><span><i />Not in scope</span><strong>2 (11%)</strong></div>
        </article>
      </div>
    </div>
  </section>
</template>
