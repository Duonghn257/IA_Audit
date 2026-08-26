<script setup lang="ts">
import cdlLogo from "../../assets/cdl-logo.png"
import cdlShieldLogo from "../../assets/cdl-shield-logo.png"

defineProps<{ error?: string }>()
defineEmits<{ login: [] }>()
</script>

<template>
  <main class="auth-page">
    <header class="auth-topbar">
      <div class="auth-brand">
        <img :src="cdlLogo" alt="City Developments Limited" />
        <span class="auth-brand-divider" aria-hidden="true" />
        <div class="auth-brand-copy">
          <strong>Operation Report Jedi</strong>
          <small>Internal Audit Workspace</small>
        </div>
      </div>
      <button class="auth-help" type="button" aria-label="Help and support" data-tooltip="Help &amp; support">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M9.8 9a2.4 2.4 0 0 1 4.6 1c0 1.8-2.4 2.1-2.4 3.8M12 17.3h.01" /></svg>
      </button>
    </header>

    <section class="auth-content">
      <div class="auth-card">
        <div class="auth-mark" aria-hidden="true">
          <img :src="cdlShieldLogo" alt="" />
        </div>
        <p class="auth-product">Operation Report Jedi</p>
        <p class="auth-subproduct">Internal Audit Workspace</p>
        <span class="auth-rule" aria-hidden="true" />
        <h1>Welcome back</h1>
        <p class="auth-copy">Sign in with your CDL account to manage<br class="auth-desktop-break" /> audit projects and draft issue logs.</p>
        <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
        <button class="google-login-button" type="button" @click="$emit('login')">
          <svg class="google-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path fill="#4285F4" stroke="none" d="M21.6 12.2c0-.7-.1-1.5-.2-2.2H12v4.3h5.4a4.6 4.6 0 0 1-2 3v2.8h3.3c1.9-1.8 2.9-4.4 2.9-7.9Z" />
            <path fill="#34A853" stroke="none" d="M12 22c2.7 0 5-.9 6.7-2.4l-3.3-2.8c-.9.6-2.1 1-3.4 1a5.9 5.9 0 0 1-5.5-4.1H3.1v2.8A10 10 0 0 0 12 22Z" />
            <path fill="#FBBC05" stroke="none" d="M6.5 13.7a6 6 0 0 1 0-3.8V7.1H3.1a10 10 0 0 0 0 9.4l3.4-2.8Z" />
            <path fill="#EA4335" stroke="none" d="M12 5.8c1.5 0 2.9.5 4 1.5l3-3A10 10 0 0 0 3.1 7.1l3.4 2.8A5.9 5.9 0 0 1 12 5.8Z" />
          </svg>
          <span>Continue with Google</span>
        </button>
      </div>

      <p class="auth-protection">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5.5 5.6v5.5c0 4.3 2.5 7.8 6.5 9.9 4-2.1 6.5-5.6 6.5-9.9V5.6L12 3Z" /><path d="m9.4 12 1.7 1.7 3.7-4" /></svg>
        Protected by CDL access controls
      </p>
    </section>
  </main>
</template>
