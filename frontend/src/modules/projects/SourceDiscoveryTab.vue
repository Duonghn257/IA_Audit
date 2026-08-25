<script setup lang="ts">
export type DiscoveryUiState = "idle" | "running" | "error" | "complete"

defineProps<{
  state: DiscoveryUiState
  correlationId?: string | null
  error?: string | null
}>()

defineEmits<{
  find: []
  retry: []
}>()

const sourceGroups = [
  { name: "AWP", count: 3, role: "SCOPE", tone: "scope" },
  { name: "APM", count: 2, role: "RISK CONTEXT", tone: "risk" },
  { name: "Process Understanding", count: 4, role: "EVIDENCE", tone: "evidence" },
  { name: "Process SOP", count: 3, role: "CRITERIA", tone: "criteria" },
]
</script>

<template>
  <section class="uat-source-tab">
    <article v-if="state === 'idle'" class="uat-find-card">
      <div>
        <span class="uat-find-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4M8 11h6m-3-3v6" /></svg></span>
        <div><h2>Find candidate issues</h2><p>Analyse the immutable source and build evidence-backed candidates for this version.</p></div>
      </div>
      <button class="uat-button uat-button-primary" type="button" @click="$emit('find')">Find candidates</button>
    </article>

    <article v-else-if="state === 'running'" class="uat-discovery-progress">
      <h2>Finding candidates</h2>
      <div class="uat-progress-steps">
        <div class="done"><b>✓</b><span><strong>Queued</strong><small>Completed</small></span></div><i />
        <div class="done"><b>✓</b><span><strong>Parsing</strong><small>Completed</small></span></div><i />
        <div class="active"><b>↻</b><span><strong>Discovering</strong><small>62%</small></span></div><i class="pending" />
        <div><b>4</b><span><strong>Validating</strong><small>Pending</small></span></div>
      </div>
      <footer><span>Job continues if you leave this page.</span><i /><span>Correlation ID:&nbsp; {{ correlationId || "9b7f2c8a-3d21-4b9f-8f2e-2a1d7c9e5b66" }}</span></footer>
    </article>

    <article v-else-if="state === 'error'" class="uat-discovery-error">
      <span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8v5m0 3h.01" /><path d="M12 3 2 21h20z" /></svg></span>
      <div><h2>INCOMPLETE: one workbook sheet could not be parsed</h2><p>{{ error || "This may affect the accuracy of candidate discovery." }}</p><small v-if="correlationId">Correlation ID: {{ correlationId }}</small></div>
      <button class="uat-button uat-button-secondary" type="button">View error</button>
      <button class="uat-button uat-button-primary" type="button" @click="$emit('retry')">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5" /><path d="M18.5 16a8 8 0 1 1 .5-9l1 5" /></svg>
        Retry
      </button>
    </article>

    <div class="uat-source-grid">
      <article class="uat-source-tree-card">
        <header><div><h2>Immutable source</h2><p>⌑&nbsp; Source frozen at project creation</p></div><span>18 files</span></header>
        <button v-for="group in sourceGroups" :key="group.name" type="button" class="uat-source-row">
          <span>›</span>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h7l2 2h9v11H3z" /></svg>
          <strong>{{ group.name }}</strong>
          <small>{{ group.count }} files</small>
          <b :class="group.tone">{{ group.role }}</b>
        </button>
        <footer><button class="uat-button uat-button-secondary uat-button-small" type="button">View source ↗</button></footer>
      </article>

      <div class="uat-coverage-column">
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
