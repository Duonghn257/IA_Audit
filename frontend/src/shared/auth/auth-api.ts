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

const AUTH_SESSION_HINT_KEY = "auth:session-active"
const LOGIN_PENDING_KEY = "auth:login-pending"

let csrfToken = ""

export class UnauthenticatedError extends Error {}

export function getCsrfToken(): string {
  return csrfToken
}

export function notifySessionExpired(): void {
  csrfToken = ""
  window.sessionStorage.removeItem(LOGIN_PENDING_KEY)
  window.sessionStorage.removeItem(AUTH_SESSION_HINT_KEY)
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT))
}

export function shouldLoadAuthSession(): boolean {
  const loginPending = window.sessionStorage.getItem(LOGIN_PENDING_KEY) === "true"
  const sessionActive = window.sessionStorage.getItem(AUTH_SESSION_HINT_KEY) === "true"
  const authError = new URLSearchParams(window.location.search).get("auth_error")

  if (authError) {
    window.sessionStorage.removeItem(LOGIN_PENDING_KEY)
    return false
  }

  return loginPending || sessionActive
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
    window.sessionStorage.removeItem(LOGIN_PENDING_KEY)
    window.sessionStorage.removeItem(AUTH_SESSION_HINT_KEY)
    throw new UnauthenticatedError()
  }
  if (!response.ok) throw new Error("Could not verify your session.")
  const session = await response.json() as AuthSession
  csrfToken = session.csrf_token
  window.sessionStorage.removeItem(LOGIN_PENDING_KEY)
  window.sessionStorage.setItem(AUTH_SESSION_HINT_KEY, "true")
  return session
}

export function startGoogleLogin(): void {
  window.sessionStorage.setItem(LOGIN_PENDING_KEY, "true")
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
  window.sessionStorage.removeItem(LOGIN_PENDING_KEY)
  window.sessionStorage.removeItem(AUTH_SESSION_HINT_KEY)
}
