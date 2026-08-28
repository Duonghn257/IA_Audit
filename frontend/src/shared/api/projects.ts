import type {
  AuditJob,
  ApiErrorBody,
  AuditProject,
  CandidateIssue,
  CreatedAuditProject,
  CreateIssueInput,
  IssuePage,
  OutputRevision,
  UpdateIssueInput,
  ProjectEvent,
  ProjectVersion,
  SourceTree,
  UploadSession,
  UploadProjectInput,
} from "../types/projects"
import { serialiseAuditorIssues } from "../auditor-inputs"
import { getCsrfToken, notifySessionExpired } from "../auth/auth-api"

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "")
const API_ROOT = `${API_BASE_URL}/api/v1`

export class ApiClientError extends Error {
  readonly code: string
  readonly correlationId: string | null
  readonly status: number

  constructor(message: string, options: { code?: string; correlationId?: string | null; status: number }) {
    super(message)
    this.name = "ApiClientError"
    this.code = options.code || "REQUEST_FAILED"
    this.correlationId = options.correlationId || null
    this.status = options.status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resolvedUrl = apiUrl(path)
  const method = (init?.method || "GET").toUpperCase()
  const headers = new Headers(init?.headers)
  const backendRequest = isBackendApiUrl(resolvedUrl)

  if (!headers.has("Accept")) headers.set("Accept", "application/json")
  if (backendRequest && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = getCsrfToken()
    if (token) headers.set("X-CSRF-Token", token)
  }

  const response = await fetch(resolvedUrl, {
    ...init,
    credentials: backendRequest ? "include" : init?.credentials,
    headers,
  })

  if (!response.ok) {
    if (response.status === 401) notifySessionExpired()
    let payload: ApiErrorBody = {}
    try {
      payload = (await response.json()) as ApiErrorBody
    } catch {
      // Preserve the stable fallback below when a proxy returns a non-JSON response.
    }
    throw new ApiClientError(payload.error?.message || `Request failed with status ${response.status}`, {
      code: payload.error?.code,
      correlationId: payload.error?.correlation_id,
      status: response.status,
    })
  }

  return (await response.json()) as T
}

function isBackendApiUrl(url: string): boolean {
  const target = new URL(url, window.location.origin)
  const apiRoot = new URL(API_ROOT, window.location.origin)
  return target.origin === apiRoot.origin && target.pathname.startsWith("/api/")
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path
  if (path.startsWith("/api/")) return `${API_BASE_URL}${path}`
  return `${API_ROOT}${path.startsWith("/") ? path : `/${path}`}`
}

export function listProjects(): Promise<AuditProject[]> {
  return request<AuditProject[]>("/projects")
}

export function getProject(projectId: string): Promise<AuditProject> {
  return request<AuditProject>(`/projects/${encodeURIComponent(projectId)}`)
}

export function getProjectSourceTree(projectId: string): Promise<SourceTree> {
  return request<SourceTree>(
    `/projects/${encodeURIComponent(projectId)}/source-documents`,
  )
}

export function listProjectEvents(projectId: string, afterEventId = 0): Promise<ProjectEvent[]> {
  return request<ProjectEvent[]>(
    `/projects/${encodeURIComponent(projectId)}/events?after_event_id=${afterEventId}`,
  )
}

export function projectEventsUrl(projectId: string, afterEventId = 0): string {
  return apiUrl(
    `/projects/${encodeURIComponent(projectId)}/events/stream?after_event_id=${afterEventId}`,
  )
}

export function uploadProject(
  input: UploadProjectInput,
  onProgress: (percent: number) => void,
): Promise<AuditProject> {
  const form = new FormData()
  if (input.name.trim()) form.append("name", input.name.trim())

  const folderRoot = input.files
    .map((file) => (file.webkitRelativePath || "").split("/").filter(Boolean)[0])
    .find(Boolean)
  const projectFiles = input.files.filter((file) => !isRootAuditorInput(file))

  for (const file of projectFiles) {
    form.append("files", file)
    form.append("relative_paths", file.webkitRelativePath || file.name)
  }

  const auditorInput = new File(
    [serialiseAuditorIssues(input.auditorIssues)],
    "sample_issues.json",
    { type: "application/json" },
  )
  form.append("files", auditorInput)
  form.append(
    "relative_paths",
    folderRoot ? `${folderRoot}/sample_issues.json` : "sample_issues.json",
  )

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", apiUrl("/projects/upload"))
    xhr.withCredentials = true
    xhr.setRequestHeader("Accept", "application/json")
    const csrfToken = getCsrfToken()
    if (csrfToken) xhr.setRequestHeader("X-CSRF-Token", csrfToken)
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    })
    xhr.addEventListener("load", () => {
      if (xhr.status === 401) notifySessionExpired()
      let payload: AuditProject | ApiErrorBody | null = null
      try {
        payload = JSON.parse(xhr.responseText) as AuditProject | ApiErrorBody
      } catch {
        // Handled by the generic error below.
      }
      if (xhr.status >= 200 && xhr.status < 300 && payload) {
        resolve(payload as AuditProject)
        return
      }
      const error = payload as ApiErrorBody | null
      reject(
        new ApiClientError(error?.error?.message || `Upload failed with status ${xhr.status}`, {
          code: error?.error?.code,
          correlationId: error?.error?.correlation_id,
          status: xhr.status,
        }),
      )
    })
    xhr.addEventListener("error", () => {
      reject(new ApiClientError("Could not connect to the audit API.", { status: 0 }))
    })
    xhr.send(form)
  })
}

export function createUploadSession(files: File[]): Promise<UploadSession> {
  return request<UploadSession>("/upload-sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      files: files.map((file) => ({
        relative_path: file.webkitRelativePath || file.name,
        size_bytes: file.size,
        content_type: file.type || null,
        modified_at: file.lastModified ? new Date(file.lastModified).toISOString() : null,
      })),
    }),
  })
}

export async function uploadSessionFiles(
  session: UploadSession,
  files: File[],
  onProgress: (percent: number, uploadedFiles: number) => void,
): Promise<UploadSession> {
  const filesByPath = new Map(
    files.map((file) => [file.webkitRelativePath || file.name, file]),
  )
  let uploadedFiles = 0

  for (const descriptor of session.files) {
    const file = filesByPath.get(descriptor.relative_path)
    if (!file) continue
    await request<unknown>(descriptor.upload_url, {
      method: descriptor.upload_method || "PUT",
      headers: {
        "Content-Type": descriptor.content_type || "application/octet-stream",
        ...descriptor.required_headers,
      },
      body: file,
    })
    uploadedFiles += 1
    onProgress(Math.round((uploadedFiles / Math.max(session.files.length, 1)) * 100), uploadedFiles)
  }

  return getUploadSession(session.session_id)
}

export function getUploadSession(sessionId: string): Promise<UploadSession> {
  return request<UploadSession>(`/upload-sessions/${encodeURIComponent(sessionId)}`)
}

export function validateUploadSession(sessionId: string): Promise<UploadSession> {
  return request<UploadSession>(`/upload-sessions/${encodeURIComponent(sessionId)}/validate`, {
    method: "POST",
  })
}

export function promoteUploadSession(
  sessionId: string,
  name: string,
): Promise<CreatedAuditProject> {
  return request<CreatedAuditProject>(
    `/upload-sessions/${encodeURIComponent(sessionId)}/projects`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    },
  )
}

export async function discardUploadSession(sessionId: string): Promise<void> {
  const response = await fetch(apiUrl(`/upload-sessions/${encodeURIComponent(sessionId)}`), {
    credentials: "include",
    method: "DELETE",
    headers: { Accept: "application/json", "X-CSRF-Token": getCsrfToken() },
  })
  if (response.status === 401) notifySessionExpired()
  if (!response.ok && response.status !== 404) {
    throw new ApiClientError(`Request failed with status ${response.status}`, {
      status: response.status,
    })
  }
}

export function listProjectVersions(projectId: string): Promise<ProjectVersion[]> {
  return request<ProjectVersion[]>(`/projects/${encodeURIComponent(projectId)}/versions`)
}

export function createProjectVersion(
  projectId: string,
  baseVersionId: string,
): Promise<ProjectVersion> {
  return request<ProjectVersion>(`/projects/${encodeURIComponent(projectId)}/versions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": createIdempotencyKey("version"),
    },
    body: JSON.stringify({ base_version_id: baseVersionId }),
  })
}

export async function listVersionIssues(projectId: string, versionId: string): Promise<CandidateIssue[]> {
  const response = await request<CandidateIssue[] | IssuePage>(
    `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/issues`,
  )
  return Array.isArray(response) ? response : response.items
}

export function getVersionIssue(projectId: string, versionId: string, issueId: string): Promise<CandidateIssue> {
  return request<CandidateIssue>(
    `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/issues/${encodeURIComponent(issueId)}`,
  )
}

export function createVersionIssue(projectId: string, versionId: string, input: CreateIssueInput): Promise<CandidateIssue> {
  return request<CandidateIssue>(
    `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/issues`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": createIdempotencyKey("issue") },
      body: JSON.stringify(input),
    },
  )
}

export function updateVersionIssue(projectId: string, versionId: string, issueId: string, issue: CandidateIssue, input: UpdateIssueInput): Promise<CandidateIssue> {
  return request<CandidateIssue>(
    `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/issues/${encodeURIComponent(issueId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...input, status: issue.status, evidence_refs: issue.evidence_refs || [], sop_refs: issue.sop_refs || [], confidence: issue.confidence, validation_flags: issue.validation_flags }),
    },
  )
}

export function setIssueDisposition(
  projectId: string,
  versionId: string,
  issueId: string,
  rowVersion: number,
  status: CandidateIssue["status"],
): Promise<CandidateIssue> {
  return request<CandidateIssue>(
    `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/issues/${encodeURIComponent(issueId)}/disposition`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ row_version: rowVersion, status }),
    },
  )
}

export function startDiscoveryJob(projectId: string, versionId: string): Promise<AuditJob> {
  return request<AuditJob>(
    `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/discovery-jobs`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": createIdempotencyKey("discovery"),
      },
      body: JSON.stringify({ force: false }),
    },
  )
}

export function getJob(jobId: string): Promise<AuditJob> {
  return request<AuditJob>(`/jobs/${encodeURIComponent(jobId)}`)
}

export function retryDiscoveryJob(jobId: string): Promise<AuditJob> {
  return request<AuditJob>(`/jobs/${encodeURIComponent(jobId)}/retry`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": createIdempotencyKey("discovery-retry"),
    },
    body: JSON.stringify({ reason: "Retry requested from project workspace" }),
  })
}

export function startAuditJob(
  projectId: string,
  versionId: string,
  issueRevision: number,
): Promise<AuditJob> {
  return request<AuditJob>(
    `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/audit-jobs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ issue_revision: issueRevision }),
    },
  )
}

export function retryAuditJob(jobId: string): Promise<AuditJob> {
  return request<AuditJob>(`/jobs/${encodeURIComponent(jobId)}/retry`, { method: "POST" })
}

export function listVersionOutputs(projectId: string, versionId: string): Promise<OutputRevision[]> {
  return request<OutputRevision[]>(
    `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/outputs`,
  )
}

function isRootAuditorInput(file: File): boolean {
  if (file.name !== "sample_issues.json") return false
  const parts = (file.webkitRelativePath || file.name).split("/").filter(Boolean)
  return parts.length <= 2
}

function createIdempotencyKey(scope: string): string {
  const id = typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `${scope}-${id}`
}
