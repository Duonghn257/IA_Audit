export type ProjectStatus =
  | "UPLOADING"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "READY_FOR_DISCOVERY"
  | "CANDIDATES_AVAILABLE"
  | "OUTPUT_AVAILABLE"

export type ProjectAction = "VIEW_STATUS" | "VIEW_PROGRESS" | "DOWNLOAD_OUTPUT"

export interface AuditProject {
  project_id: string
  name: string
  source_type: string
  status: ProjectStatus
  current_activity: string | null
  allowed_actions: ProjectAction[]
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
  output_available: boolean
  output_download_url: string | null
  version: string | null
  issue_count: number | null
  error: string | null
  raw_expires_at: string | null
  raw_deleted_at: string | null
}

export interface ProjectEvent {
  event_id: number
  stage: string
  message: string
  completed_steps: number
  total_steps: number
  warning: boolean
  occurred_at: string
}

export interface ApiErrorBody {
  error?: {
    code?: string
    message?: string
    details?: Record<string, unknown>
    correlation_id?: string | null
  }
}

export interface UploadProjectInput {
  name: string
  files: File[]
  auditorIssues: AuditorIssueInput[]
}

export interface AuditorIssueInput {
  title_hint: string
  observed_gap: string
  evidence_summary: string
  evidence_refs: string[]
  sop_refs: string[]
  risk_category: string
}

export type UploadSessionState =
  | "UPLOADING"
  | "VALIDATING"
  | "READY_TO_CREATE"
  | "INVALID"
  | "PROMOTED"
  | "EXPIRED"

export type LogicalRole = "SCOPE" | "RISK_CONTEXT" | "EVIDENCE" | "CRITERIA" | "CONTEXT"

export interface SourceFile {
  document_id: string
  name: string
  relative_path: string
  logical_role: LogicalRole
  size_bytes: number
  content_type: string | null
  status: string
  parse_status: string
}

export interface SourceFolder {
  name: string
  logical_role: LogicalRole
  file_count: number
  files: SourceFile[]
}

export interface SourceTree {
  snapshot_id: string
  status: string
  folder_count: number
  file_count: number
  total_size_bytes: number
  folders: SourceFolder[]
}

export interface UploadSessionFile {
  file_id: string
  relative_path: string
  size_bytes: number
  content_type: string | null
  modified_at: string | null
  upload_status: string
  logical_role: LogicalRole | null
  readability_status: string | null
  validation_message: string | null
  upload_method: string
  upload_url: string
  required_headers: Record<string, string>
}

export interface UploadSession {
  session_id: string
  state: UploadSessionState
  created_at: string
  expires_at: string
  promoted_at: string | null
  files: UploadSessionFile[]
  validation_report: UploadValidationReport | null
  allowed_actions: string[]
  action_reasons: Record<string, string>
}

export interface UploadValidationMessage {
  code: string
  message: string
  file_id: string | null
  relative_path: string | null
  blocking: boolean
  details?: Record<string, unknown>
}

export interface UploadValidationReport {
  valid: boolean
  errors: UploadValidationMessage[]
  warnings: UploadValidationMessage[]
  role_summary: Record<Exclude<LogicalRole, "CONTEXT">, number>
}

export type AuditVersionState =
  | "DRAFT"
  | "CANDIDATES_READY"
  | "AUDITING"
  | "DOCX_READY"
  | "STALE_OUTPUT"

export type JobState = "QUEUED" | "RUNNING" | "SUCCEEDED" | "INCOMPLETE" | "FAILED"
export type JobType = "DISCOVERY" | "AUDIT"

export interface AuditJob {
  job_id: string
  project_id: string
  project_version_id: string
  job_type: JobType
  state: JobState
  stage: string | null
  completed_items: number
  total_items: number | null
  current_message: string | null
  attempt_count: number
  correlation_id: string
  created_at: string
  updated_at: string
  heartbeat_at: string | null
  error: string | null
}

export interface ProjectVersion {
  version_id: string
  project_id: string
  sequence_no: number
  label: string
  base_version_id: string | null
  state: AuditVersionState
  issue_revision: number
  issue_counts: Record<string, number>
  latest_job: AuditJob | null
  output_available: boolean
  allowed_actions: string[]
  created_at: string
  updated_at: string
}

export type IssueOrigin = "AI_DISCOVERED" | "MANUAL"
export type IssueStatus =
  | "DRAFT"
  | "READY_FOR_REVIEW"
  | "APPROVED"
  | "NEEDS_EVIDENCE"
  | "REJECTED"
  | "OUT_OF_SCOPE"

export interface SourceReference {
  reference_id: string
  ref_kind: "EVIDENCE" | "CRITERIA"
  document_id: string
  unit_id: string | null
  location: Record<string, unknown>
  quote: string | null
}

export interface CandidateIssue {
  issue_id: string
  project_version_id: string
  origin: IssueOrigin
  status: IssueStatus
  observed_gap: string
  title_hint: string | null
  evidence_summary: string | null
  risk_category: string | null
  confidence: number | null
  validation_flags: string[]
  row_version: number
  source_refs: SourceReference[]
  created_at: string
  updated_at: string
}

export interface OutputRevision {
  output_id: string
  project_version_id: string
  ordinal: number
  status: "CURRENT" | "STALE"
  filename: string
  content_hash: string
  created_at: string
  download_url: string
}

export interface CreatedAuditProject {
  project_id: string
  name: string
  state: "READY_FOR_DISCOVERY" | "CANDIDATES_AVAILABLE" | "OUTPUT_AVAILABLE"
  source_snapshot_id: string
  version: {
    version_id: string
    sequence_no: number
    label: string
    state: AuditVersionState
    issue_revision: number
  }
  created_at: string
  updated_at: string
}
