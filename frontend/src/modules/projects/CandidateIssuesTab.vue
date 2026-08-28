<script setup lang="ts">
import { computed, ref, watch } from "vue";
import PrimaryButton from "../../shared/ui/PrimaryButton.vue"

import IssueEditorModal from "./IssueEditorModal.vue";
import type {
  CandidateIssue,
  CreateIssueInput,
  IssueStatus,
  UpdateIssueInput,
} from "../../shared/types/projects";

const props = defineProps<{
  issues: CandidateIssue[];
  loading?: boolean;
  saving?: boolean;
  error?: string;
}>();
const emit = defineEmits<{
  audit: [];
  create: [input: CreateIssueInput];
  disposition: [issue: CandidateIssue, status: IssueStatus];
  retry: [];
  select: [issueId: string];
  update: [issue: CandidateIssue, input: UpdateIssueInput];
}>();

const selectedId = ref(props.issues[0]?.issue_id || "");
interface IssueEditorValue {
  title_hint: string;
  observed_gap: string;
  evidence_summary: string;
  risk_category: string;
}

const issueModalMode = ref<"create" | "edit" | null>(null);
const activeIssueModalMode = computed(() => issueModalMode.value || "create");
const selectedIssue = computed(
  () =>
    props.issues.find((item) => item.issue_id === selectedId.value) ||
    props.issues[0] ||
    null,
);
const approvedCount = computed(
  () => props.issues.filter((item) => item.status === "APPROVED").length,
);
const warningCount = computed(
  () => props.issues.filter((item) => item.validation_flags.length > 0).length,
);
const modalInitialValue = computed<IssueEditorValue>(() => {
  if (issueModalMode.value !== "edit" || !selectedIssue.value) {
    return { title_hint: "", observed_gap: "", evidence_summary: "", risk_category: "" };
  }
  return {
    title_hint: selectedIssue.value.title_hint || "",
    observed_gap: selectedIssue.value.observed_gap,
    evidence_summary: selectedIssue.value.evidence_summary || "",
    risk_category: selectedIssue.value.risk_category || "",
  };
});
const referenceKinds = ["EVIDENCE", "CRITERIA"] as const;
const dispositionOptions: { status: IssueStatus; label: string }[] = [
  { status: "APPROVED", label: "Approve" },
  { status: "NEEDS_EVIDENCE", label: "Needs evidence" },
  { status: "REJECTED", label: "Reject" },
  { status: "OUT_OF_SCOPE", label: "Out of scope" },
];

watch(
  () => props.issues,
  (issues) => {
    if (!issues.some((item) => item.issue_id === selectedId.value))
      selectedId.value = issues[0]?.issue_id || "";
  },
  { deep: true },
);

function retry(): void {
  emit("retry");
}
function startAudit(): void {
  emit("audit");
}
function chooseDisposition(status: IssueStatus): void {
  if (selectedIssue.value) emit("disposition", selectedIssue.value, status);
}
function selectIssue(issueId: string): void {
  selectedId.value = issueId;
  emit("select", issueId);
}
function originLabel(issue: CandidateIssue): string {
  return issue.origin === "MANUAL" ? "Manual" : "AI discovered";
}
function statusLabel(status: IssueStatus): string {
  return status
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/^./, (letter) => letter.toUpperCase());
}
function confidence(issue: CandidateIssue): string {
  return issue.confidence === null
    ? "N/A"
    : `${Math.round(issue.confidence * 100)}%`;
}
function isCriteria(reference: CandidateIssue["source_refs"][number]): boolean {
  return reference.ref_kind === "CRITERIA";
}
function referenceLocation(
  reference: CandidateIssue["source_refs"][number],
): string {
  const values = Object.values(reference.location)
    .filter((value) => value !== null && value !== "")
    .join(" • ");
  return `${reference.document_id}${values ? ` • ${values}` : ""}`;
}
function openCreateModal(): void {
  issueModalMode.value = "create";
}
function openEditModal(): void {
  if (selectedIssue.value) issueModalMode.value = "edit";
}
function closeIssueModal(): void {
  issueModalMode.value = null;
}
function submitIssueForm(form: IssueEditorValue): void {
  const titleHint = form.title_hint.trim() || null;
  const observedGap = form.observed_gap.trim();
  const evidenceSummary = form.evidence_summary.trim() || null;
  const riskCategory = form.risk_category.trim() || null;
  if (!observedGap) return;

  if (issueModalMode.value === "create") {
    emit("create", {
      observed_gap: observedGap,
      title_hint: titleHint,
      evidence_summary: evidenceSummary,
      risk_category: riskCategory,
      status: "DRAFT",
      source_refs: [],
    });
  } else {
    const issue = selectedIssue.value;
    if (!issue) return;
    emit("update", issue, {
      row_version: issue.row_version,
      title_hint: titleHint,
      observed_gap: observedGap,
      evidence_summary: evidenceSummary,
      risk_category: riskCategory,
      source_refs: issue.source_refs.map(
        ({ ref_kind, document_id, unit_id, location, quote }) => ({
          ref_kind, document_id, unit_id, location, quote,
        }),
      ),
    });
  }
  closeIssueModal();
}
</script>

<template>
  <section class="uat-candidate-tab">
    <div v-if="error" class="uat-candidate-feedback error">
      <span>{{ error }}</span><button type="button" @click="retry">Retry</button>
    </div>
    <div class="uat-candidate-workspace">
      <aside class="uat-candidate-register">
        <header>
          <div>
            <h2>Candidate Issue Register</h2>
            <span>{{ issues.length }} issues</span>
          </div>
          <PrimaryButton size="small" type="button" @click="openCreateModal">+ Add issue</PrimaryButton>
        </header>
        <div class="uat-candidate-list">
          <p v-if="loading" class="uat-candidate-empty">Loading issues…</p>
          <p v-else-if="!issues.length" class="uat-candidate-empty">
            No candidate issues yet.
          </p>
          <button v-for="(issue, index) in issues" :key="issue.issue_id" type="button"
            :class="{ active: selectedIssue?.issue_id === issue.issue_id }" @click="selectIssue(issue.issue_id)">
            <b>{{ index + 1 }}</b>
            <span><strong>{{ issue.title_hint || issue.observed_gap }}</strong><small><i
                  :class="issue.origin.toLowerCase()">{{
                    originLabel(issue)
                  }}</i><em>{{ confidence(issue) }}</em></small></span>
            <span class="uat-candidate-status" :class="issue.status.toLowerCase()"><i />{{ statusLabel(issue.status)
              }}</span>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m9 6 6 6-6 6" />
            </svg>
          </button>
          <footer v-if="issues.length">
            Showing 1 to {{ issues.length }} of {{ issues.length }} issues
          </footer>
        </div>
      </aside>

      <article v-if="selectedIssue" class="uat-issue-detail">
        <header class="uat-issue-detail-title">
          <b>{{
            Math.max(
              1,
              issues.findIndex(
                (item) => item.issue_id === selectedIssue?.issue_id,
              ) + 1,
            )
          }}</b>
          <div>
            <h2>
              {{ selectedIssue.title_hint || selectedIssue.observed_gap }}
            </h2>
            <p>
              <span>{{ originLabel(selectedIssue) }}</span>{{ confidence(selectedIssue) }} confidence
            </p>
          </div>
          <div class="uat-issue-title-actions">
            <PrimaryButton class="uat-modify-button" size="small" type="button"
              @click="openEditModal">
              Modify
            </PrimaryButton>
          </div>
        </header>

        <div class="uat-issue-detail-body">
          <div class="uat-issue-field">
            <strong>Observed gap</strong>
            <p>{{ selectedIssue.observed_gap }}</p>
          </div>
          <div class="uat-issue-field">
            <strong>Evidence summary</strong>
            <p>
              {{
                selectedIssue.evidence_summary || "No evidence summary supplied."
              }}
            </p>
          </div>
          <div class="uat-issue-field">
            <strong>Risk category</strong>
            <p>
              <span v-if="selectedIssue.risk_category" class="uat-risk-chip">{{
                selectedIssue.risk_category
                }}</span><span v-else>Not specified</span>
            </p>
          </div>

          <section class="uat-references-card">
            <template v-for="kind in referenceKinds" :key="kind">
              <h3>
                {{
                  kind === "EVIDENCE"
                    ? "Evidence references"
                    : "Criteria references"
                }}
              </h3>
              <p v-if="
                !selectedIssue.source_refs.some(
                  (reference) => reference.ref_kind === kind,
                )
              " class="uat-reference-empty">
                No {{ kind.toLowerCase() }} references.
              </p>
              <button v-for="reference in selectedIssue.source_refs.filter(
                (item) => item.ref_kind === kind,
              )" :key="reference.reference_id" type="button">
                <span>▣&nbsp; {{ reference.document_id }}
                  <b :class="{ criteria: isCriteria(reference) }">{{
                    kind
                    }}</b></span><small>{{ referenceLocation(reference) }} ↗</small>
              </button>
            </template>
        </section>

          <section class="uat-disposition-card">
            <h3>Disposition</h3>
            <div>
              <button v-for="option in dispositionOptions" :key="option.status"
                :class="{ active: selectedIssue.status === option.status }" :disabled="saving" type="button"
                @click="chooseDisposition(option.status)">
                <i />{{ option.label }}
              </button>
            </div>
          </section>
        </div>
      </article>
      <div v-else-if="!loading" class="uat-issue-detail uat-candidate-empty">
        Select an issue or create a manual issue.
      </div>
    </div>

    <IssueEditorModal
      :open="issueModalMode !== null"
      :mode="activeIssueModalMode"
      :initial-value="modalInitialValue"
      :saving="saving"
      @close="closeIssueModal"
      @submit="submitIssueForm"
    />
    <footer class="uat-audit-preflight">
      <span>♢&nbsp; Audit preflight</span><strong>{{ approvedCount }} approved issues</strong><i v-if="warningCount" />
      <b v-if="warningCount">{{ warningCount }} warning{{ warningCount === 1 ? "" : "s" }}</b><PrimaryButton :disabled="!approvedCount" type="button" @click="startAudit">
        ▷&nbsp; Audit current version
      </PrimaryButton>
    </footer>
  </section>
</template>
