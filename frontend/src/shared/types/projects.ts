export type ProjectStatus = "UPLOADING" | "PROCESSING" | "COMPLETED" | "FAILED"

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
}
