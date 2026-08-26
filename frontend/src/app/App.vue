<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue"
import ProjectsWorkspaceV2 from "../modules/projects/ProjectsWorkspaceV2.vue"
import { getAuthSession, logout, startGoogleLogin, SESSION_EXPIRED_EVENT, UnauthenticatedError } from "../shared/auth/auth-api"
import type { AuthSession } from "../shared/auth/auth-api"
import LoginView from "../shared/auth/LoginView.vue"

const session = ref<AuthSession | null>(null)
const checkingSession = ref(true)
const authError = ref("")
const sessionExpired = ref(false)
const loggingOut = ref(false)

function showSessionExpired(): void {
  if (session.value) sessionExpired.value = true
}

function returnToLogin(): void {
  sessionExpired.value = false
  session.value = null
  window.history.replaceState({}, "", "/")
}

onMounted(async () => {
  window.addEventListener(SESSION_EXPIRED_EVENT, showSessionExpired)
  try {
    session.value = await getAuthSession()
  } catch (error) {
    if (!(error instanceof UnauthenticatedError)) {
      authError.value = error instanceof Error ? error.message : "Could not verify your session."
    }
  } finally {
    checkingSession.value = false
  }
})

onBeforeUnmount(() => window.removeEventListener(SESSION_EXPIRED_EVENT, showSessionExpired))

async function handleLogout(): Promise<void> {
  if (!session.value || loggingOut.value) return
  loggingOut.value = true
  try {
    await logout(session.value.csrf_token)
    session.value = null
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div v-if="checkingSession" class="auth-loading"><span /><p>Checking your session...</p></div>
  <ProjectsWorkspaceV2 v-else-if="session" :auth-session="session" :logging-out="loggingOut" @logout="handleLogout" />
  <LoginView v-else :error="authError" @login="startGoogleLogin" />
  <div v-if="sessionExpired" class="session-expired-backdrop">
    <section class="session-expired-dialog" role="alertdialog" aria-modal="true" aria-labelledby="session-expired-title">
      <div class="session-expired-icon" aria-hidden="true">!</div>
      <h2 id="session-expired-title">Phi&#234;n &#273;&#227; h&#7871;t h&#7841;n</h2>
      <p>Phi&#234;n c&#7911;a b&#7841;n &#273;&#227; h&#7871;t h&#7841;n, vui l&#242;ng quay l&#7841;i trang &#273;&#259;ng nh&#7853;p.</p>
      <button type="button" autofocus @click="returnToLogin">OK</button>
    </section>
  </div>
</template>
