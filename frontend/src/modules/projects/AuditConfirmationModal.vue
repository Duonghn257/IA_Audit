<script setup lang="ts">
import { ref, watch } from "vue"
import PrimaryButton from "../../shared/ui/PrimaryButton.vue"

const props = defineProps<{
  open: boolean
  versionLabel: string
  approvedCount: number
  submitting: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: []
}>()

const acknowledged = ref(true)

watch(() => props.open, (open) => {
  if (open) acknowledged.value = true
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="uat-modal-backdrop" role="presentation" @mousedown.self="emit('close')">
      <section class="uat-audit-modal" role="dialog" aria-modal="true" aria-labelledby="uat-audit-title">
        <header>
          <span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 4 6v5c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10V6z" /><path d="m9 12 2 2 4-5" /></svg></span>
          <div><small>Audit current version</small><h2 id="uat-audit-title">Audit {{ versionLabel }}?</h2></div>
        </header>
        <p>Audit will use a frozen snapshot of the {{ approvedCount || 5 }} approved issues below.<br />Changes made after submission will not affect this run.</p>
        <dl>
          <div><dt>Version</dt><dd>{{ versionLabel }}</dd></div>
          <div><dt>Approved issues</dt><dd>{{ approvedCount || 5 }}</dd></div>
          <div><dt>Preflight</dt><dd class="warning">1 warning</dd></div>
          <div><dt>Output</dt><dd>New revision</dd></div>
        </dl>
        <div class="uat-audit-warning"><span>△</span><p>1 manual issue has no evidence references.<br />It can proceed under the manual-issue policy.</p></div>
        <button class="uat-snapshot-toggle" type="button">View approved issue snapshot <span>⌄</span></button>
        <label class="uat-snapshot-check"><input v-model="acknowledged" type="checkbox" /><span>✓</span>I understand this run uses a frozen input snapshot.</label>
        <footer><button class="uat-button uat-button-secondary" type="button" :disabled="submitting" @click="emit('close')">Cancel</button><PrimaryButton type="button" :disabled="!acknowledged || submitting" @click="emit('confirm')">{{ submitting ? "Starting…" : "Start audit" }}</PrimaryButton></footer>
      </section>
    </div>
  </Teleport>
</template>
