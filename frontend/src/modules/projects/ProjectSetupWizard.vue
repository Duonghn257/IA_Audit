<script setup lang="ts">
import { computed, ref, watch } from "vue"

import {
  AuditorInputParseError,
  createEmptyAuditorIssue,
  parseAuditorIssuesJson,
  sourceArtifactReference,
} from "../../shared/auditor-inputs"
import { formatBytes } from "../../shared/formatting/date"
import type {
  AuditorIssueInput,
  UploadProjectInput,
} from "../../shared/types/projects"

type WizardStep = 1 | 2 | 3
type ReferenceField = "evidence_refs" | "sop_refs"

const props = defineProps<{
  open: boolean
  uploading: boolean
  progress: number
  error: string
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: UploadProjectInput]
}>()

const folderInput = ref<HTMLInputElement | null>(null)
const jsonInput = ref<HTMLInputElement | null>(null)
const step = ref<WizardStep>(1)
const projectName = ref("")
const files = ref<File[]>([])
const issues = ref<AuditorIssueInput[]>([createEmptyAuditorIssue()])
const selectedIssueIndex = ref(0)
const validationMessage = ref("")
const importMessage = ref("")

const folderName = computed(() => {
  const firstPath = files.value[0]?.webkitRelativePath
  return firstPath?.split("/").filter(Boolean)[0] || "Selected folder"
})

const totalBytes = computed(() =>
  files.value.reduce((total, file) => total + file.size, 0),
)

const rootIssuesFile = computed(() =>
  files.value.find((file) => isRootAuditorInput(file)) || null,
)

const currentIssue = computed<AuditorIssueInput>(
  () => issues.value[selectedIssueIndex.value] || issues.value[0]!,
)

const artifactReferences = computed(() => {
  const paths = files.value
    .map(sourceArtifactReference)
    .filter((path): path is string => path !== null)
  return [...new Set(paths)].sort((left, right) => left.localeCompare(right))
})

const requiredInputsComplete = computed(() =>
  issues.value.length > 0 && issues.value.every(issueIsComplete),
)

const reviewWarnings = computed(() => {
  const warnings: string[] = []
  const folderRoles = new Set(
    artifactReferences.value
      .map((path) => path.split("/")[0]?.toLowerCase())
      .filter(Boolean),
  )
  const expectedFolders = [
    ["awp", "AWP folder was not found."],
    ["apm", "APM folder was not found."],
    ["process understanding", "Process Understanding folder was not found."],
  ] as const

  for (const [folder, message] of expectedFolders) {
    if (!folderRoles.has(folder)) warnings.push(message)
  }

  issues.value.forEach((issue, index) => {
    if (!issue.evidence_refs.length) {
      warnings.push("Issue " + (index + 1) + " has no supporting evidence reference.")
    }
    if (!issue.sop_refs.length) {
      warnings.push("Issue " + (index + 1) + " has no SOP reference.")
    }
  })
  return warnings
})

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    resetWizard()
  },
)

function resetWizard(): void {
  step.value = 1
  projectName.value = ""
  files.value = []
  issues.value = [createEmptyAuditorIssue()]
  selectedIssueIndex.value = 0
  validationMessage.value = ""
  importMessage.value = ""
  if (folderInput.value) folderInput.value.value = ""
  if (jsonInput.value) jsonInput.value.value = ""
}

function chooseFolder(): void {
  if (!props.uploading) folderInput.value?.click()
}

function chooseJson(): void {
  if (!props.uploading) jsonInput.value?.click()
}

function onFolderSelected(event: Event): void {
  const target = event.target as HTMLInputElement
  files.value = Array.from(target.files || [])
  validationMessage.value = ""
  importMessage.value = ""

  if (!files.value.length) return
  if (!projectName.value.trim()) {
    projectName.value = folderName.value.replace(/[_-]+/g, " ")
  }
}

async function onJsonSelected(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) await importIssues(file, file.name)
  target.value = ""
}

async function loadFolderJson(): Promise<void> {
  const file = rootIssuesFile.value
  if (file) await importIssues(file, "sample_issues.json from the selected folder")
}

async function importIssues(file: File, sourceLabel: string): Promise<void> {
  validationMessage.value = ""
  importMessage.value = ""
  try {
    issues.value = parseAuditorIssuesJson(await file.text())
    selectedIssueIndex.value = 0
    importMessage.value =
      "Loaded " + issues.value.length + " issues from " + sourceLabel + ". Review them before continuing."
  } catch (error) {
    validationMessage.value =
      error instanceof AuditorInputParseError
        ? error.message
        : "Could not read the selected JSON file."
  }
}

function goToInputs(): void {
  validationMessage.value = ""
  if (!files.value.length) {
    validationMessage.value = "Choose a project folder first."
    return
  }
  step.value = 2
}

function addIssue(): void {
  issues.value.push(createEmptyAuditorIssue())
  selectedIssueIndex.value = issues.value.length - 1
  validationMessage.value = ""
}

function removeIssue(index: number): void {
  if (issues.value.length === 1) {
    issues.value = [createEmptyAuditorIssue()]
    selectedIssueIndex.value = 0
    return
  }
  issues.value.splice(index, 1)
  selectedIssueIndex.value = Math.min(selectedIssueIndex.value, issues.value.length - 1)
}

function issueIsComplete(issue: AuditorIssueInput): boolean {
  return Boolean(issue.observed_gap.trim() && issue.evidence_summary.trim())
}

function issueLabel(issue: AuditorIssueInput, index: number): string {
  const label = issue.title_hint.trim() || issue.observed_gap.trim()
  return label || "Untitled issue " + (index + 1)
}

function referenceOptions(field: ReferenceField): string[] {
  const selected = new Set(currentIssue.value[field])
  const candidates =
    field === "sop_refs"
      ? artifactReferences.value.filter((path) =>
          path.toLowerCase().startsWith("process sop/"),
        )
      : artifactReferences.value
  return candidates.filter((path) => !selected.has(path))
}

function addReference(event: Event, field: ReferenceField): void {
  const select = event.target as HTMLSelectElement
  const value = select.value
  if (value && !currentIssue.value[field].includes(value)) {
    currentIssue.value[field].push(value)
  }
  select.value = ""
}

function removeReference(field: ReferenceField, reference: string): void {
  currentIssue.value[field] = currentIssue.value[field].filter(
    (value) => value !== reference,
  )
}

function goToReview(): void {
  validationMessage.value = ""
  const invalidIndex = issues.value.findIndex((issue) => !issueIsComplete(issue))
  if (invalidIndex >= 0) {
    selectedIssueIndex.value = invalidIndex
    validationMessage.value =
      "Complete the observed gap and evidence summary for Issue " + (invalidIndex + 1) + "."
    return
  }
  step.value = 3
}

function submit(): void {
  if (!requiredInputsComplete.value || props.uploading) return
  emit("submit", {
    name: projectName.value,
    files: files.value,
    auditorIssues: issues.value.map((issue) => ({
      ...issue,
      evidence_refs: [...issue.evidence_refs],
      sop_refs: [...issue.sop_refs],
    })),
  })
}

function close(): void {
  if (!props.uploading) emit("close")
}

function isRootAuditorInput(file: File): boolean {
  if (file.name !== "sample_issues.json") return false
  const parts = (file.webkitRelativePath || file.name).split("/").filter(Boolean)
  return parts.length <= 2
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop project-wizard-backdrop" role="presentation" @mousedown.self="close">
      <section
        v-if="step === 1"
        class="upload-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-title"
      >
        <div class="dialog-header">
          <div>
            <span class="eyebrow">New audit project</span>
            <h2 id="upload-title">Project & artefacts</h2>
            <p>Name the audit project and select its complete local artefact folder.</p>
          </div>
          <button class="icon-button" type="button" aria-label="Close" @click="close">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
          </button>
        </div>

        <div class="dialog-body">
          <label class="field-label" for="project-name">Project name <span>Optional</span></label>
          <input
            id="project-name"
            v-model="projectName"
            class="text-input"
            type="text"
            maxlength="255"
            placeholder="e.g. SAP Ariba Access Controls Review"
          />

          <input
            ref="folderInput"
            class="visually-hidden"
            type="file"
            webkitdirectory
            directory
            multiple
            @change="onFolderSelected"
          />

          <button
            class="folder-dropzone"
            :class="{ selected: files.length > 0 }"
            type="button"
            @click="chooseFolder"
          >
            <span class="folder-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M3.5 7.5h6l2-2h9a1.5 1.5 0 0 1 1.5 1.5v11.5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 1.5-2Z" /><path d="M12 11v6m-3-3 3-3 3 3" /></svg>
            </span>
            <template v-if="files.length">
              <strong>{{ folderName }}</strong>
              <span>{{ files.length }} files · {{ formatBytes(totalBytes) }}</span>
              <small>Choose a different folder</small>
            </template>
            <template v-else>
              <strong>Choose a folder</strong>
              <span>Select the complete folder from your computer</span>
              <small>Auditor inputs will be added in the next step</small>
            </template>
          </button>

          <div class="requirement" :class="{ valid: files.length }">
            <span class="requirement-mark" aria-hidden="true">
              <svg v-if="files.length" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
              <svg v-else viewBox="0 0 24 24"><path d="M12 8v5m0 3h.01" /><circle cx="12" cy="12" r="9" /></svg>
            </span>
            <div>
              <strong>Auditor inputs are entered separately</strong>
              <span>You can enter issues manually or import JSON after choosing the folder.</span>
            </div>
          </div>

          <p v-if="validationMessage" class="form-error" role="alert">{{ validationMessage }}</p>
        </div>

        <div class="dialog-footer">
          <button class="button button-secondary" type="button" @click="close">Cancel</button>
          <button class="button button-primary" type="button" :disabled="!files.length" @click="goToInputs">
            Continue
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>
          </button>
        </div>
      </section>

      <section
        v-else
        class="project-setup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="setup-title"
      >
        <header class="setup-header">
          <div class="setup-title">
            <span class="eyebrow">New audit project</span>
            <h2 id="setup-title">{{ step === 2 ? "Auditor inputs" : "Review & run" }}</h2>
            <p>{{ projectName || folderName }}</p>
          </div>

          <ol class="setup-steps" aria-label="Project setup progress">
            <li class="complete"><span>1</span><div><small>Project</small><strong>Artefacts</strong></div></li>
            <li :class="{ active: step === 2, complete: step === 3 }"><span>2</span><div><small>Auditor</small><strong>Inputs</strong></div></li>
            <li :class="{ active: step === 3 }"><span>3</span><div><small>Review</small><strong>Run</strong></div></li>
          </ol>

          <button class="icon-button" type="button" :disabled="uploading" aria-label="Close" @click="close">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
          </button>
        </header>

        <template v-if="step === 2">
          <div class="setup-toolbar">
            <div>
              <strong>Define the issues AI should draft</strong>
              <span>Observed gap and evidence summary are required for every issue.</span>
            </div>
            <div class="toolbar-actions">
              <input ref="jsonInput" class="visually-hidden" type="file" accept=".json,application/json" @change="onJsonSelected" />
              <button class="button button-secondary button-small" type="button" @click="chooseJson">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m-4 4 4-4 4 4" /><path d="M5 20h14" /></svg>
                Import JSON
              </button>
              <button class="button button-primary button-small" type="button" @click="addIssue">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
                Add issue
              </button>
            </div>
          </div>

          <div v-if="rootIssuesFile" class="folder-json-banner">
            <span>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v5h5M10 13h5m-5 4h5" /></svg>
            </span>
            <div>
              <strong>Existing sample_issues.json found</strong>
              <small>Load its content into the form, then review or edit it before running.</small>
            </div>
            <button class="text-action" type="button" @click="loadFolderJson">Load into form</button>
          </div>

          <div class="issue-workspace">
            <aside class="issue-navigator">
              <div class="issue-nav-heading">
                <span>Issues</span>
                <strong>{{ issues.length }}</strong>
              </div>
              <div class="issue-nav-list">
                <button
                  v-for="(issue, index) in issues"
                  :key="index"
                  class="issue-nav-item"
                  :class="{ active: selectedIssueIndex === index }"
                  type="button"
                  @click="selectedIssueIndex = index"
                >
                  <span class="issue-number">{{ index + 1 }}</span>
                  <span class="issue-nav-copy">
                    <strong>{{ issueLabel(issue, index) }}</strong>
                    <small>{{ issueIsComplete(issue) ? "Ready" : "Input required" }}</small>
                  </span>
                  <span class="issue-state" :class="{ ready: issueIsComplete(issue) }">
                    <svg v-if="issueIsComplete(issue)" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
                    <i v-else />
                  </span>
                </button>
              </div>
              <button class="add-issue-nav" type="button" @click="addIssue">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
                Add another issue
              </button>
            </aside>

            <main class="issue-editor">
              <div class="issue-editor-heading">
                <div>
                  <span>Issue {{ selectedIssueIndex + 1 }} of {{ issues.length }}</span>
                  <h3>{{ issueLabel(currentIssue, selectedIssueIndex) }}</h3>
                </div>
                <button class="delete-issue" type="button" @click="removeIssue(selectedIssueIndex)">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14M10 11v6m4-6v6" /></svg>
                  {{ issues.length === 1 ? "Clear issue" : "Delete issue" }}
                </button>
              </div>

              <div class="issue-form">
                <div class="form-field full">
                  <label for="title-hint">Title hint <span>Optional</span></label>
                  <input
                    id="title-hint"
                    v-model="currentIssue.title_hint"
                    class="text-input"
                    type="text"
                    placeholder="e.g. Privileged access should be segregated by job function"
                  />
                  <small>AI will refine this into the approved positive-title style.</small>
                </div>

                <div class="form-field full">
                  <label for="observed-gap">Observed gap <b>*</b></label>
                  <textarea
                    id="observed-gap"
                    v-model="currentIssue.observed_gap"
                    class="text-area"
                    rows="5"
                    placeholder="Describe what was observed during fieldwork and how it differs from the expected control."
                  />
                  <small>State the actual condition. Avoid describing only what you planned to audit.</small>
                </div>

                <div class="form-field full">
                  <label for="evidence-summary">Evidence summary <b>*</b></label>
                  <textarea
                    id="evidence-summary"
                    v-model="currentIssue.evidence_summary"
                    class="text-area"
                    rows="4"
                    placeholder="Summarise the supporting test result, sample size, exceptions or walkthrough evidence."
                  />
                </div>

                <div class="form-field">
                  <label for="risk-category">Risk category <span>Optional</span></label>
                  <select id="risk-category" v-model="currentIssue.risk_category" class="select-input">
                    <option value="">Select a category</option>
                    <option>Compliance</option>
                    <option>IT</option>
                    <option>Operational</option>
                    <option>Financial</option>
                    <option>Strategic</option>
                  </select>
                </div>

                <div class="form-field full">
                  <label for="evidence-reference">Evidence references <span>Recommended</span></label>
                  <select id="evidence-reference" class="select-input" @change="addReference($event, 'evidence_refs')">
                    <option value="">Select an uploaded artefact…</option>
                    <option v-for="reference in referenceOptions('evidence_refs')" :key="reference" :value="reference">
                      {{ reference }}
                    </option>
                  </select>
                  <div v-if="currentIssue.evidence_refs.length" class="reference-chips">
                    <span v-for="reference in currentIssue.evidence_refs" :key="reference">
                      {{ reference }}
                      <button type="button" aria-label="Remove evidence reference" @click="removeReference('evidence_refs', reference)">×</button>
                    </span>
                  </div>
                </div>

                <div class="form-field full">
                  <label for="sop-reference">SOP references <span>Recommended</span></label>
                  <select id="sop-reference" class="select-input" @change="addReference($event, 'sop_refs')">
                    <option value="">Select a Process SOP artefact…</option>
                    <option v-for="reference in referenceOptions('sop_refs')" :key="reference" :value="reference">
                      {{ reference }}
                    </option>
                  </select>
                  <div v-if="currentIssue.sop_refs.length" class="reference-chips">
                    <span v-for="reference in currentIssue.sop_refs" :key="reference">
                      {{ reference }}
                      <button type="button" aria-label="Remove SOP reference" @click="removeReference('sop_refs', reference)">×</button>
                    </span>
                  </div>
                </div>
              </div>
            </main>
          </div>

          <div v-if="importMessage" class="inline-message success" role="status">{{ importMessage }}</div>
          <div v-if="validationMessage" class="inline-message error" role="alert">{{ validationMessage }}</div>
        </template>

        <template v-else>
          <div class="review-workspace">
            <div class="review-main">
              <section class="review-card">
                <div class="review-card-heading">
                  <div><span>Project</span><h3>{{ projectName || folderName }}</h3></div>
                  <button class="text-action" type="button" :disabled="uploading" @click="step = 1">Edit</button>
                </div>
                <dl class="review-facts">
                  <div><dt>Source folder</dt><dd>{{ folderName }}</dd></div>
                  <div><dt>Artefacts</dt><dd>{{ files.length }} files · {{ formatBytes(totalBytes) }}</dd></div>
                  <div><dt>Auditor inputs</dt><dd>{{ issues.length }} issues</dd></div>
                </dl>
              </section>

              <section class="review-card">
                <div class="review-card-heading">
                  <div><span>Auditor inputs</span><h3>Issues ready for drafting</h3></div>
                  <button class="text-action" type="button" :disabled="uploading" @click="step = 2">Edit</button>
                </div>
                <div class="review-issues">
                  <article v-for="(issue, index) in issues" :key="index">
                    <span>{{ index + 1 }}</span>
                    <div>
                      <strong>{{ issueLabel(issue, index) }}</strong>
                      <p>{{ issue.observed_gap }}</p>
                      <small>{{ issue.evidence_refs.length }} evidence refs · {{ issue.sop_refs.length }} SOP refs</small>
                    </div>
                    <svg viewBox="0 0 24 24" aria-label="Ready"><path d="m5 12 4 4L19 6" /></svg>
                  </article>
                </div>
              </section>
            </div>

            <aside class="review-sidebar">
              <section class="readiness-card">
                <span class="readiness-icon">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 4 6v5c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10V6z" /><path d="m9 12 2 2 4-5" /></svg>
                </span>
                <h3>Ready to process</h3>
                <p>The submitted issues will be saved as the project’s auditor input and used by the drafting pipeline.</p>
              </section>

              <section v-if="reviewWarnings.length" class="warning-card">
                <div><strong>{{ reviewWarnings.length }} review notes</strong><span>These do not block the POC run.</span></div>
                <ul>
                  <li v-for="warning in reviewWarnings" :key="warning">{{ warning }}</li>
                </ul>
              </section>

              <div v-if="error && !uploading" class="inline-message error wizard-upload-error" role="alert">
                {{ error }}
              </div>

              <div v-if="uploading" class="upload-progress" aria-live="polite">
                <div class="progress-copy"><span>Uploading securely…</span><strong>{{ progress }}%</strong></div>
                <div class="progress-track"><span :style="{ width: progress + '%' }" /></div>
                <small>Keep this window open until processing begins.</small>
              </div>
            </aside>
          </div>
        </template>

        <footer class="setup-footer">
          <button class="button button-secondary" type="button" :disabled="uploading" @click="step === 2 ? (step = 1) : (step = 2)">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 5-7 7 7 7" /></svg>
            Back
          </button>
          <div>
            <span v-if="step === 2">{{ issues.filter(issueIsComplete).length }} of {{ issues.length }} issues complete</span>
            <button
              v-if="step === 2"
              class="button button-primary"
              type="button"
              :disabled="!requiredInputsComplete"
              @click="goToReview"
            >
              Review & continue
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>
            </button>
            <button
              v-else
              class="button button-primary"
              type="button"
              :disabled="uploading"
              @click="submit"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m-5-5 5 5 5-5" /><path d="M5 20h14" /></svg>
              {{ uploading ? "Uploading…" : "Upload & process" }}
            </button>
          </div>
        </footer>
      </section>
    </div>
  </Teleport>
</template>
