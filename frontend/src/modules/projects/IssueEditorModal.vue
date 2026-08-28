<script setup lang="ts">
import { reactive, ref, watch } from "vue";

interface IssueEditorValue {
  title_hint: string;
  observed_gap: string;
  evidence_summary: string;
  risk_category: string;
}

const props = defineProps<{
  open: boolean;
  mode: "create" | "edit";
  initialValue: IssueEditorValue;
  saving?: boolean;
}>();
const emit = defineEmits<{
  close: [];
  submit: [value: IssueEditorValue];
}>();

const riskCategoryOptions = ["Compliance", "Operational", "Strategic", "Financial"] as const;
const riskOpen = ref(false);
const form = reactive<IssueEditorValue>({ title_hint: "", observed_gap: "", evidence_summary: "", risk_category: "" });

watch(() => props.open, (open) => {
  if (!open) return;
  Object.assign(form, props.initialValue);
  riskOpen.value = false;
}, { immediate: true });

function close(): void { riskOpen.value = false; emit("close"); }
function selectRisk(category: string): void { form.risk_category = category; riskOpen.value = false; }
function clearRisk(): void { selectRisk(""); }
function submit(): void { if (form.observed_gap.trim()) emit("submit", { ...form }); }
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="uat-modal-backdrop uat-issue-modal-backdrop" @mousedown.self="close">
      <section class="uat-issue-modal" role="dialog" aria-modal="true" :aria-labelledby="`issue-editor-${mode}-title`">
        <header>
          <h2 :id="`issue-editor-${mode}-title`">{{ mode === "create" ? "Create manual issue" : "Modify issue information" }}</h2>
          <button type="button" aria-label="Close" @click="close">×</button>
        </header>
        <form class="uat-issue-editor" @submit.prevent="submit">
          <label>Title<input v-model="form.title_hint" /></label>
          <label>Observed gap<textarea v-model="form.observed_gap" rows="8" required /></label>
          <label>Evidence summary<textarea v-model="form.evidence_summary" rows="8" /></label>
          <div class="uat-custom-select-field">
            <span>Risk category</span>
            <div class="uat-custom-select">
              <button class="uat-custom-select-trigger" :class="{ open: riskOpen }" type="button"
                aria-haspopup="listbox" :aria-expanded="riskOpen" @click="riskOpen = !riskOpen">
                <span :class="{ placeholder: !form.risk_category }">{{ form.risk_category || "Select a risk category" }}</span>
                <i aria-hidden="true" />
              </button>
              <div v-if="riskOpen" class="uat-custom-select-options" role="listbox">
                <button type="button" role="option" :aria-selected="!form.risk_category"
                  :class="{ selected: !form.risk_category }" @click="clearRisk">Select a risk category</button>
                <button v-for="category in riskCategoryOptions" :key="category" type="button" role="option"
                  :aria-selected="form.risk_category === category"
                  :class="{ selected: form.risk_category === category }" @click="selectRisk(category)">{{ category }}</button>
              </div>
            </div>
          </div>
          <footer>
            <button class="uat-button uat-button-secondary" type="button" @click="close">Cancel</button>
            <button class="uat-button uat-button-primary" :disabled="saving" type="submit">
              {{ saving ? (mode === "create" ? "Creating…" : "Saving…") : (mode === "create" ? "Create issue" : "Save changes") }}
            </button>
          </footer>
        </form>
      </section>
    </div>
  </Teleport>
</template>
