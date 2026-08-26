<script setup lang="ts">
import { computed, ref, watch } from "vue"
import type { ProjectVersion } from "../../shared/types/projects"

const props = defineProps<{
  open: boolean
  projectName: string
  versions: ProjectVersion[]
  initialBaseVersionId: string
  nextVersionLabel: string
  submitting: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  close: []
  confirm: [baseVersionId: string]
}>()

const selectedBaseVersionId = ref("")
const baseMenuOpen = ref(false)
const selectedBaseVersion = computed(() => props.versions.find((version) => version.version_id === selectedBaseVersionId.value) || props.versions[0])

watch(() => props.open, (open) => {
  if (open) {
    selectedBaseVersionId.value = props.initialBaseVersionId
    baseMenuOpen.value = false
  }
}, { immediate: true })

function selectBaseVersion(versionId: string): void {
  selectedBaseVersionId.value = versionId
  baseMenuOpen.value = false
}

</script>

<template>
  <Teleport to="body">
    <Transition name="uat-version-modal">
      <div v-if="open" class="uat-modal-backdrop" role="presentation" @mousedown.self="!submitting && emit('close')" @keydown.esc="baseMenuOpen ? baseMenuOpen = false : !submitting && emit('close')">
        <section class="uat-version-modal" role="dialog" aria-modal="true" aria-labelledby="uat-version-modal-title">
          <header>
            <span class="uat-version-modal-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M12 3v18M3 12h18" /></svg>
            </span>
            <div>
              <small>New audit version</small>
              <h2 id="uat-version-modal-title">Create {{ nextVersionLabel }}?</h2>
            </div>
            <button class="uat-version-modal-close" type="button" aria-label="Close" :disabled="submitting" @click="emit('close')">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
            </button>
          </header>

          <p>Create a clean audit workspace for <strong>{{ projectName }}</strong>, based on {{ selectedBaseVersion?.label }}.</p>

          <dl>
            <div><dt>New version</dt><dd>{{ nextVersionLabel }}</dd></div>
            <div class="uat-version-base-field">
              <dt>Based on</dt>
              <dd>
                <button class="uat-modal-base-select" :class="{ open: baseMenuOpen }" type="button" aria-haspopup="listbox" :aria-expanded="baseMenuOpen" @click="baseMenuOpen = !baseMenuOpen">
                  <span>{{ selectedBaseVersion?.label }}</span>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5" /></svg>
                </button>
                <Transition name="uat-version-menu">
                  <div v-if="baseMenuOpen" class="uat-modal-base-menu" role="listbox" aria-label="Base version">
                    <button v-for="version in versions" :key="version.version_id" class="uat-modal-base-option" :class="{ selected: version.version_id === selectedBaseVersionId }" type="button" role="option" :aria-selected="version.version_id === selectedBaseVersionId" @click="selectBaseVersion(version.version_id)">
                      <span><strong>{{ version.label }}</strong><small>{{ version.base_version_id ? "Derived version" : "Initial version" }}</small></span>
                      <svg v-if="version.version_id === selectedBaseVersionId" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>
                    </button>
                  </div>
                </Transition>
              </dd>
            </div>
          </dl>

          <div class="uat-version-inheritance">
            <div class="included">
              <span aria-hidden="true">✓</span>
              <p><strong>Immutable source is shared</strong><small>The same frozen project files remain available.</small></p>
            </div>
            <div>
              <span aria-hidden="true">○</span>
              <p><strong>Audit workspace starts empty</strong><small>Candidates, jobs and outputs are not copied.</small></p>
            </div>
          </div>

          <p v-if="error" class="uat-version-modal-error" role="alert">{{ error }}</p>

          <footer>
            <button class="uat-button uat-button-secondary" type="button" :disabled="submitting" @click="emit('close')">Cancel</button>
            <button class="uat-button uat-button-primary" type="button" :disabled="submitting || !selectedBaseVersionId" @click="emit('confirm', selectedBaseVersionId)">
              <span v-if="submitting" class="uat-button-spinner" aria-hidden="true" />
              {{ submitting ? "Creating…" : `Create ${nextVersionLabel}` }}
            </button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
