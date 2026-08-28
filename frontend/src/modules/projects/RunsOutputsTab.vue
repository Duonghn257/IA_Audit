<script setup lang="ts">
import { computed } from "vue"
import PrimaryButton from "../../shared/ui/PrimaryButton.vue"

import { formatDate } from "../../shared/formatting/date"
import type { AuditJob, JobEvent, OutputRevision } from "../../shared/types/projects"

const props = defineProps<{
  jobs: AuditJob[]
  outputs: OutputRevision[]
  events: JobEvent[]
  projectName: string
  versionLabel: string
}>()

const emit = defineEmits<{
  download: [output: OutputRevision]
  retry: [job: AuditJob]
}>()

const stages = ["PARSING", "CONTEXT", "CONSTRAINTS", "DRAFTING", "CRITIQUING", "STYLING", "VALIDATING", "RENDERING"] as const
const displayJobs = computed(() => props.jobs)
const activeJob = computed(() => displayJobs.value.find((job) => job.job_type === "AUDIT" && ["QUEUED", "RUNNING"].includes(job.state)) || null)
const currentOutput = computed(() => props.outputs.find((output) => output.status === "CURRENT") || props.outputs[0] || null)
const activeStageIndex = computed(() => activeJob.value?.stage ? stages.indexOf(activeJob.value.stage as typeof stages[number]) : -1)
const progressPercent = computed(() => {
  if (!activeJob.value) return 0
  return Math.min(100, Math.round((activeJob.value.completed_items / Math.max(activeJob.value.total_items || stages.length, 1)) * 100))
})
const latestMessage = computed(() => props.events.at(-1)?.message || activeJob.value?.current_message || "Audit is queued and will start shortly.")

function runTitle(job: AuditJob): string {
  return job.job_type === "AUDIT" ? "Audit run" : "Discovery run"
}

function runSummary(job: AuditJob): string {
  if (["FAILED", "INCOMPLETE"].includes(job.state)) return job.error || job.current_message || "The run did not complete"
  if (["QUEUED", "RUNNING"].includes(job.state)) return job.current_message || job.stage || "Preparing"
  return job.job_type === "AUDIT"
    ? "Drafting · Validation · Rendering"
    : "Parsing · Discovery · Validation"
}

function outputTitle(output: OutputRevision): string {
  return output.status === "CURRENT" ? output.filename : `Revision ${output.ordinal}`
}

function stateLabel(job: AuditJob): string {
  return job.state.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase())
}

function stageState(index: number): "done" | "active" | "pending" {
  if (index < activeStageIndex.value) return "done"
  if (index === activeStageIndex.value) return "active"
  return "pending"
}
</script>

<template>
  <section class="uat-runs-tab">
    <article v-if="activeJob" class="uat-discovery-progress uat-run-progress" aria-live="polite">
      <header class="uat-discovery-progress-header">
        <h2>Running audit</h2>
        <div><span>{{ latestMessage }}</span><i /><span>Correlation ID:&nbsp; {{ activeJob.correlation_id }}</span></div>
      </header>
      <div class="uat-progress-steps uat-audit-progress-steps">
        <template v-for="(stage, index) in stages" :key="stage">
          <div :class="stageState(index)">
            <b>{{ stageState(index) === "done" ? "✓" : stageState(index) === "active" ? "↻" : index + 1 }}</b>
            <span><strong>{{ stage.replaceAll("_", " ") }}</strong><small>{{ stageState(index) === "done" ? "Completed" : stageState(index) === "active" ? `${progressPercent}%` : "Pending" }}</small></span>
          </div>
        </template>
      </div>
      <footer>Job continues if you leave this page.</footer>
    </article>

    <article v-if="currentOutput" class="uat-output-ready">
      <span>✓</span>
      <div><h2>Draft issue log is ready</h2><p>Generated from the approved {{ versionLabel }} issue snapshot.</p></div>
      <PrimaryButton type="button" @click="emit('download', currentOutput)">⇩&nbsp; Download DOCX</PrimaryButton>
    </article>

    <div v-if="!activeJob && !displayJobs.length && !outputs.length" class="uat-runs-empty">
      <span>▷</span>
      <h2>No audit run yet</h2>
      <p>Review candidate issues, approve at least one, then choose “Audit current version”.</p>
    </div>

    <div v-if="displayJobs.length || outputs.length" class="uat-runs-grid">
      <article class="uat-runs-card">
        <h2>Runs</h2>
        <p v-if="!displayJobs.length" class="uat-runs-list-empty">No audit runs for this version.</p>
        <div v-for="job in displayJobs" :key="job.job_id" class="uat-run-row">
          <span :class="job.state.toLowerCase()">{{ job.state === "SUCCEEDED" ? "✓" : ["RUNNING", "QUEUED"].includes(job.state) ? "◌" : "!" }}</span>
          <div><strong>{{ runTitle(job) }}</strong><small>{{ runSummary(job) }}</small></div>
          <b :class="job.state.toLowerCase()">{{ stateLabel(job) }}</b>
          <time>{{ formatDate(job.updated_at) }}</time>
          <button v-if="['FAILED', 'INCOMPLETE'].includes(job.state)" type="button" @click="emit('retry', job)">Retry</button>
        </div>
      </article>

      <article class="uat-outputs-card">
        <h2>Output revisions</h2>
        <p v-if="!outputs.length" class="uat-runs-list-empty">An output revision will appear after rendering completes.</p>
        <button v-for="output in outputs" :key="output.output_id" type="button" class="uat-output-row" @click="emit('download', output)">
          <span>▤</span>
          <div><strong>{{ outputTitle(output) }}</strong><small>Revision {{ output.ordinal }} · {{ formatDate(output.created_at) }}</small></div>
          <b :class="output.status.toLowerCase()">{{ output.status }}</b>
          <i>⇩</i>
        </button>
        <footer v-if="outputs.length">ⓘ&nbsp;&nbsp; Previous outputs remain available.</footer>
      </article>
    </div>
  </section>
</template>
