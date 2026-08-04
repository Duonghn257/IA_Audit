import type { AuditorIssueInput } from "./types/projects"

const SOURCE_ARTEFACT_FOLDERS = new Set([
  "APM",
  "AWP",
  "Guidelines",
  "Process SOP",
  "Process Understanding",
  "Samples",
])
const SUPPORTED_ARTEFACT_EXTENSIONS = new Set([".docx", ".pdf", ".xlsx"])

export class AuditorInputParseError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "AuditorInputParseError"
  }
}

export function createEmptyAuditorIssue(): AuditorIssueInput {
  return {
    title_hint: "",
    observed_gap: "",
    evidence_summary: "",
    evidence_refs: [],
    sop_refs: [],
    risk_category: "",
  }
}

export function sourceArtifactReference(
  file: Pick<File, "name" | "webkitRelativePath">,
): string | null {
  const fullParts = (file.webkitRelativePath || file.name)
    .split("/")
    .filter(Boolean)
  const relativeParts = fullParts.length > 1 ? fullParts.slice(1) : fullParts
  if (relativeParts.length !== 2) return null

  const [folder, filename] = relativeParts
  if (!folder || !filename || !SOURCE_ARTEFACT_FOLDERS.has(folder)) return null
  if (filename.startsWith(".") || filename.startsWith("~$")) return null

  const extensionIndex = filename.lastIndexOf(".")
  const extension = extensionIndex >= 0 ? filename.slice(extensionIndex).toLowerCase() : ""
  if (!SUPPORTED_ARTEFACT_EXTENSIONS.has(extension)) return null

  return folder + "/" + filename
}

export function parseAuditorIssuesJson(text: string): AuditorIssueInput[] {
  let payload: unknown
  try {
    payload = JSON.parse(text)
  } catch {
    throw new AuditorInputParseError("The selected file is not valid JSON.")
  }

  if (!Array.isArray(payload) || payload.length === 0) {
    throw new AuditorInputParseError("The JSON must contain a non-empty array of audit issues.")
  }

  return payload.map((item, index) => normaliseIssue(item, index))
}

export function serialiseAuditorIssues(issues: AuditorIssueInput[]): string {
  return JSON.stringify(
    issues.map((issue) => ({
      title_hint: issue.title_hint.trim(),
      observed_gap: issue.observed_gap.trim(),
      evidence_summary: issue.evidence_summary.trim(),
      evidence_refs: cleanStringList(issue.evidence_refs),
      sop_refs: cleanStringList(issue.sop_refs),
      risk_category: issue.risk_category.trim(),
    })),
    null,
    2,
  )
}

function normaliseIssue(item: unknown, index: number): AuditorIssueInput {
  if (!item || typeof item !== "object" || Array.isArray(item)) {
    throw new AuditorInputParseError(`Issue ${index + 1} must be a JSON object.`)
  }

  const value = item as Record<string, unknown>
  const observedGap = requiredString(value.observed_gap, index, "observed_gap")
  const evidenceSummary = requiredString(value.evidence_summary, index, "evidence_summary")

  return {
    title_hint: optionalString(value.title_hint, index, "title_hint"),
    observed_gap: observedGap,
    evidence_summary: evidenceSummary,
    evidence_refs: optionalStringList(value.evidence_refs, index, "evidence_refs"),
    sop_refs: optionalStringList(value.sop_refs, index, "sop_refs"),
    risk_category: optionalString(value.risk_category, index, "risk_category"),
  }
}

function requiredString(value: unknown, index: number, field: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new AuditorInputParseError(`Issue ${index + 1}: ${field} is required.`)
  }
  return value.trim()
}

function optionalString(value: unknown, index: number, field: string): string {
  if (value === undefined || value === null) return ""
  if (typeof value !== "string") {
    throw new AuditorInputParseError(`Issue ${index + 1}: ${field} must be text.`)
  }
  return value.trim()
}

function optionalStringList(value: unknown, index: number, field: string): string[] {
  if (value === undefined || value === null) return []
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
    throw new AuditorInputParseError(`Issue ${index + 1}: ${field} must be an array of text values.`)
  }
  return cleanStringList(value as string[])
}

function cleanStringList(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))]
}
