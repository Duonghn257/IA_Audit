export interface AuthUser {
  user_id: string
  email: string
  display_name: string
  picture_url: string | null
  hosted_domain: string | null
  provider: string
}

export interface AuthSession {
  auth_enabled: boolean
  csrf_token: string
  expires_at: string | null
  user: AuthUser
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "")
const AUTH_ROOT = `${API_BASE_URL}/api/v1/auth`
export const SESSION_EXPIRED_EVENT = "auth:session-expired"

let csrfToken = ""

export class UnauthenticatedError extends Error {}

export function getCsrfToken(): string {
  return csrfToken
}

export function notifySessionExpired(): void {
  csrfToken = ""
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT))
}

export async function getAuthSession(): Promise<AuthSession> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 10_000)
  let response: Response
  try {
    response = await fetch(`${AUTH_ROOT}/me`, {
      credentials: "include",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Session check timed out. Please reload and try again.")
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
  if (response.status === 401) {
    csrfToken = ""
    throw new UnauthenticatedError()
  }
  if (!response.ok) throw new Error("Could not verify your session.")
  const session = await response.json() as AuthSession
  csrfToken = session.csrf_token
  return session
}

export function startGoogleLogin(): void {
  window.location.assign(`${AUTH_ROOT}/google/login`)
}

export async function logout(token: string): Promise<void> {
  const response = await fetch(`${AUTH_ROOT}/logout`, {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "X-CSRF-Token": token,
    },
  })
  if (response.status === 401) {
    notifySessionExpired()
    return
  }
  if (!response.ok) throw new Error("Could not sign out.")
  csrfToken = ""
}
