<script setup lang="ts">
import cdlLogo from "../../assets/cdl-logo.png"

withDefaults(defineProps<{
  environment?: string
  runningJobs?: number
  primaryLabel?: string
}>(), {
  environment: "UAT environment",
  runningJobs: 0,
  primaryLabel: "New project",
})

defineEmits<{
  primary: []
}>()
</script>

<template>
  <header class="uat-topbar">
    <div class="uat-brand-lockup">
      <img :src="cdlLogo" alt="City Developments Limited" />
      <span aria-hidden="true" />
      <div>
        <strong>Audit Report</strong>
        <small>Workspace</small>
      </div>
    </div>
    <div class="uat-topbar-actions">
      <span v-if="runningJobs" class="uat-environment"><i />{{ runningJobs }} job running</span>
      <span v-else class="uat-environment"><i />{{ environment }}</span>
      <button class="uat-button uat-button-primary" type="button" @click="$emit('primary')">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        {{ primaryLabel }}
      </button>
    </div>
  </header>
</template>
