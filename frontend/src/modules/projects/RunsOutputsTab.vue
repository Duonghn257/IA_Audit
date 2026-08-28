<script setup lang="ts">
import { computed } from "vue"
import PrimaryButton from "../../shared/ui/PrimaryButton.vue"

import { formatDate } from "../../shared/formatting/date"
import type { AuditJob, OutputRevision } from "../../shared/types/projects"

const props = defineProps<{
  jobs: AuditJob[]
  outputs: OutputRevision[]
  projectName: string
  versionLabel: string
}>()

defineEmits<{
  download: [output: OutputRevision | null]
}>()

const displayRuns = computed(() => props.jobs.length ? props.jobs : [
  { job_id: "demo-audit", job_type: "AUDIT", state: "SUCCEEDED", updated_at: "2026-08-24T11:19:00Z", stage: "Drafting · Validation · Rendering" },
  { job_id: "demo-discovery", job_type: "DISCOVERY", state: "SUCCEEDED", updated_at: "2026-08-24T10:32:00Z", stage: "Parsing · Discovery · Validation" },
] as const)

const displayOutputs = computed(() => props.outputs.length ? props.outputs : [
  { output_id: "demo-r2", project_version_id: "demo", ordinal: 2, status: "CURRENT", filename: `${props.projectName.replaceAll(" ", "_")}_Issue Log ${props.versionLabel}.docx`, content_hash: "", created_at: "2026-08-24T11:19:00Z", download_url: "" },
  { output_id: "demo-r1", project_version_id: "demo", ordinal: 1, status: "STALE", filename: "Revision 1", content_hash: "", created_at: "2026-08-23T11:19:00Z", download_url: "" },
] satisfies OutputRevision[])

function runTitle(job: (typeof displayRuns.value)[number]): string {
  return job.job_type === "AUDIT" ? "Audit run" : "Discovery run"
}
</script>

<template>
  <section class="uat-runs-tab">
    <article class="uat-output-ready">
      <span>✓</span>
      <div><h2>Draft issue log is ready</h2><p>Generated from the approved {{ versionLabel }} issue snapshot.</p></div>
      <PrimaryButton type="button" @click="$emit('download', outputs[0] || null)">⇩&nbsp; Download DOCX</PrimaryButton>
    </article>

    <div class="uat-runs-grid">
      <article class="uat-runs-card">
        <h2>Runs</h2>
        <div v-for="job in displayRuns" :key="job.job_id" class="uat-run-row">
          <span>✓</span>
          <div><strong>{{ runTitle(job) }}</strong><small>{{ job.stage || "Preparing" }}</small></div>
          <b :class="job.state.toLowerCase()">{{ job.state === "SUCCEEDED" ? "Succeeded" : job.state }}</b>
          <time>{{ formatDate(job.updated_at) }}</time>
        </div>
      </article>

      <article class="uat-outputs-card">
        <h2>Output revisions</h2>
        <button v-for="output in displayOutputs" :key="output.output_id" type="button" class="uat-output-row" @click="$emit('download', output)">
          <span>▤</span>
          <div><strong>{{ output.ordinal === 1 ? "Revision 1" : output.filename }}</strong><small>{{ output.ordinal > 1 ? `Revision ${output.ordinal} · ` : "" }}{{ formatDate(output.created_at) }}</small></div>
          <b :class="output.status.toLowerCase()">{{ output.status }}</b>
          <i>⇩</i>
        </button>
        <footer>ⓘ&nbsp;&nbsp; Previous outputs remain available.</footer>
      </article>
    </div>
  </section>
</template>
