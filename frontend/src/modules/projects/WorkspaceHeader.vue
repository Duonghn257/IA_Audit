<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue"
import cdlLogo from "../../assets/cdl-logo.png"
import type { AuthUser } from "../../shared/auth/auth-api"

const props = withDefaults(defineProps<{
  environment?: string
  runningJobs?: number
  primaryLabel?: string
  user: AuthUser
  loggingOut?: boolean
}>(), {
  environment: "UAT environment",
  runningJobs: 0,
  primaryLabel: "New project",
  loggingOut: false,
})

defineEmits<{ primary: []; logout: [] }>()

const accountOpen = ref(false)
const initials = computed(() => props.user.display_name
  .split(/\s+/)
  .filter(Boolean)
  .slice(0, 2)
  .map((part) => part[0])
  .join("")
  .toUpperCase())

function closeAccount(): void {
  if (!props.loggingOut) accountOpen.value = false
}

function closeOnEscape(event: KeyboardEvent): void {
  if (event.key === "Escape") closeAccount()
}

window.addEventListener("keydown", closeOnEscape)
onBeforeUnmount(() => window.removeEventListener("keydown", closeOnEscape))
</script>

<template>
  <header class="uat-topbar">
    <div class="uat-brand-lockup">
      <img :src="cdlLogo" alt="City Developments Limited" />
      <span aria-hidden="true" />
      <div>
        <strong>Operation Report Jedi</strong>
        <small>Internal Audit Workspace</small>
      </div>
    </div>

    <div class="uat-topbar-actions">
      <span v-if="runningJobs" class="uat-environment"><i />{{ runningJobs }} job running</span>
      <span v-else class="uat-environment"><i />{{ environment }}</span>
      <button class="uat-button uat-button-primary" type="button" @click="$emit('primary')">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        {{ primaryLabel }}
      </button>
      <button class="account-trigger" type="button" :aria-expanded="accountOpen" aria-controls="account-drawer" aria-label="Open account" @click="accountOpen = true">
        <img v-if="user.picture_url" :src="user.picture_url" alt="" referrerpolicy="no-referrer" />
        <span v-else>{{ initials }}</span>
      </button>
    </div>
  </header>

  <Transition name="account-mask">
    <button v-if="accountOpen" class="account-scrim" type="button" aria-label="Close account panel" @click="closeAccount" />
  </Transition>

  <Transition name="account-panel">
    <aside v-if="accountOpen" id="account-drawer" class="account-drawer" aria-label="Account">
      <div class="account-drawer-heading">
        <strong>Account</strong>
        <button type="button" aria-label="Close account panel" :disabled="loggingOut" @click="closeAccount">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
        </button>
      </div>

      <div class="account-profile">
        <img v-if="user.picture_url" :src="user.picture_url" alt="" referrerpolicy="no-referrer" />
        <span v-else>{{ initials }}</span>
        <strong>{{ user.display_name }}</strong>
        <small>{{ user.email }}</small>
      </div>

      <div class="account-provider">
        <svg class="google-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#4285F4" stroke="none" d="M21.6 12.2c0-.7-.1-1.5-.2-2.2H12v4.3h5.4a4.6 4.6 0 0 1-2 3v2.8h3.3c1.9-1.8 2.9-4.4 2.9-7.9Z" />
          <path fill="#34A853" stroke="none" d="M12 22c2.7 0 5-.9 6.7-2.4l-3.3-2.8c-.9.6-2.1 1-3.4 1a5.9 5.9 0 0 1-5.5-4.1H3.1v2.8A10 10 0 0 0 12 22Z" />
          <path fill="#FBBC05" stroke="none" d="M6.5 13.7a6 6 0 0 1 0-3.8V7.1H3.1a10 10 0 0 0 0 9.4l3.4-2.8Z" />
          <path fill="#EA4335" stroke="none" d="M12 5.8c1.5 0 2.9.5 4 1.5l3-3A10 10 0 0 0 3.1 7.1l3.4 2.8A5.9 5.9 0 0 1 12 5.8Z" />
        </svg>
        <span>Signed in with Google</span>
      </div>

      <div class="account-session">
        <i aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3 5.5 5.6v5.5c0 4.3 2.5 7.8 6.5 9.9 4-2.1 6.5-5.6 6.5-9.9V5.6L12 3Z" /><path d="m9.4 12 1.7 1.7 3.7-4" /></svg></i>
        <strong>Active session</strong>
        <span aria-hidden="true" />
      </div>

      <button class="account-logout" type="button" :disabled="loggingOut" @click="$emit('logout')">
        <span v-if="loggingOut" class="account-logout-spinner" aria-hidden="true" />
        <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M10 4H5v16h5M14 8l4 4-4 4M8 12h10" /></svg>
        <span>Sign out</span>
      </button>
    </aside>
  </Transition>
</template>
