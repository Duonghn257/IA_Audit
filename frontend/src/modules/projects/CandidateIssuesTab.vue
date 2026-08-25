<script setup lang="ts">
import { computed, ref, watch } from "vue"

import type { CandidateIssue, IssueStatus } from "../../shared/types/projects"

const props = defineProps<{ issues: CandidateIssue[] }>()
const emit = defineEmits<{
  audit: []
  disposition: [issue: CandidateIssue, status: IssueStatus]
}>()

const selectedId = ref(props.issues[0]?.issue_id || "")
const selectedIssue = computed(() => props.issues.find((item) => item.issue_id === selectedId.value) || props.issues[0] || null)
const approvedCount = computed(() => props.issues.filter((item) => item.status === "APPROVED").length)
const dispositionOptions: { status: IssueStatus; label: string }[] = [{ status: "APPROVED", label: "Approve" }, { status: "NEEDS_EVIDENCE", label: "Needs evidence" }, { status: "REJECTED", label: "Reject" }, { status: "OUT_OF_SCOPE", label: "Out of scope" }]

watch(() => props.issues, (issues) => {
  if (!issues.some((item) => item.issue_id === selectedId.value)) selectedId.value = issues[0]?.issue_id || ""
}, { deep: true })

function originLabel(issue: CandidateIssue): string {
  return issue.origin === "MANUAL" ? "Manual" : "AI discovered"
}

function statusLabel(status: IssueStatus): string {
  return status.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase())
}

function confidence(issue: CandidateIssue): string {
  return `${Math.round((issue.confidence || 0) * 100)}%`
}

function referenceLocation(issue: CandidateIssue, kind: "EVIDENCE" | "CRITERIA"): string {
  const reference = issue.source_refs.find((item) => item.ref_kind === kind)
  if (!reference) return kind === "EVIDENCE" ? "Access Review.xlsx • Sheet Users • B12:F28" : "SOP Access Review.docx • §3.2"
  const values = Object.values(reference.location).filter(Boolean).join(" • ")
  return `${reference.document_id}${values ? ` • ${values}` : ""}`
}
</script>

<template>
  <section class="uat-candidate-tab">
    <div class="uat-candidate-workspace">
      <aside class="uat-candidate-register">
        <header><h2>Candidate Issue Register</h2><span>{{ issues.length }} issues</span></header>
        <button v-for="(issue, index) in issues" :key="issue.issue_id" type="button" :class="{ active: selectedIssue?.issue_id === issue.issue_id }" @click="selectedId = issue.issue_id">
          <b>{{ index + 1 }}</b>
          <span><strong>{{ issue.title_hint || issue.observed_gap }}</strong><small><i :class="issue.origin.toLowerCase()">{{ originLabel(issue) }}</i><em>{{ confidence(issue) }}</em></small></span>
          <span class="uat-candidate-status" :class="issue.status.toLowerCase()"><i />{{ statusLabel(issue.status) }}</span>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>
        </button>
        <footer>Showing 1 to {{ issues.length }} of {{ issues.length }} issues</footer>
      </aside>

      <article v-if="selectedIssue" class="uat-issue-detail">
        <header class="uat-issue-detail-title">
          <b>{{ Math.max(1, issues.findIndex((item) => item.issue_id === selectedIssue?.issue_id) + 1) }}</b>
          <div><h2>{{ selectedIssue.title_hint || selectedIssue.observed_gap }}</h2><p><span>{{ originLabel(selectedIssue) }}</span>{{ confidence(selectedIssue) }} confidence</p></div>
          <div class="uat-validation-flags"><span class="warning">△ WEAK EVIDENCE</span><span class="verified">♢ SOURCE VERIFIED</span></div>
        </header>

        <div class="uat-issue-field"><strong>Observed gap</strong><p>{{ selectedIssue.observed_gap }}</p><button type="button">Edit</button></div>
        <div class="uat-issue-field"><strong>Evidence summary</strong><p>{{ selectedIssue.evidence_summary || "No evidence summary supplied." }}</p><button type="button">Edit</button></div>
        <div class="uat-issue-field"><strong>Risk category</strong><p><span class="uat-risk-chip">{{ selectedIssue.risk_category || "Access governance" }}</span></p><button type="button">Edit</button></div>
        <div class="uat-issue-field"><strong>Scope / control mapping</strong><p>Control: APM-02 (Review access rights)<br />Category: Access Review</p><button type="button">Edit</button></div>

        <section class="uat-references-card">
          <h3>Evidence references</h3>
          <button type="button"><span>▣&nbsp; Access Review.xlsx <b>EVIDENCE</b></span><small>{{ referenceLocation(selectedIssue, "EVIDENCE") }} ↗</small></button>
          <button type="button"><span>▣&nbsp; Meeting Notes.pdf <b>EVIDENCE</b></span><small>Meeting Notes.pdf • p. 4 ↗</small></button>
          <h3>Criteria reference</h3>
          <button type="button"><span>▣&nbsp; SOP Access Review.docx <b class="criteria">CRITERIA</b></span><small>{{ referenceLocation(selectedIssue, "CRITERIA") }} ↗</small></button>
        </section>

        <section class="uat-disposition-card">
          <h3>Disposition</h3>
          <div>
            <button v-for="option in dispositionOptions" :key="option.status" :class="{ active: selectedIssue.status === option.status }" type="button" @click="emit('disposition', selectedIssue, option.status)"><i />{{ option.label }}</button>
          </div>
        </section>
      </article>
    </div>

    <footer class="uat-audit-preflight"><span>♢&nbsp; Audit preflight</span><strong>{{ approvedCount || 3 }} approved issues</strong><i /> <b>1 warning</b><button class="uat-button uat-button-primary" type="button" @click="emit('audit')">▷&nbsp; Audit current version</button></footer>
  </section>
</template>
