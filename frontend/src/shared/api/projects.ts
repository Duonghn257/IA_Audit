import type {
  ApiErrorBody,
  AuditProject,
  ProjectEvent,
  UploadProjectInput,
} from "../types/projects"
import { serialiseAuditorIssues } from "../auditor-inputs"

const API_ROOT = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "")

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
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  })

  if (!response.ok) {
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

export function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path
  if (path.startsWith("/api/")) return path
  return `${API_ROOT}${path.startsWith("/") ? path : `/${path}`}`
}

export function listProjects(): Promise<AuditProject[]> {
  return request<AuditProject[]>("/projects")
}

export function getProject(projectId: string): Promise<AuditProject> {
  return request<AuditProject>(`/projects/${encodeURIComponent(projectId)}`)
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
    xhr.setRequestHeader("Accept", "application/json")
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    })
    xhr.addEventListener("load", () => {
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

function isRootAuditorInput(file: File): boolean {
  if (file.name !== "sample_issues.json") return false
  const parts = (file.webkitRelativePath || file.name).split("/").filter(Boolean)
  return parts.length <= 2
}
