<script setup lang="ts">
withDefaults(defineProps<{
  type?: "button" | "submit" | "reset"
  disabled?: boolean
  size?: "default" | "small"
}>(), {
  type: "button",
  disabled: false,
  size: "default",
})
</script>

<template>
  <button
    class="uat-button uat-button-primary"
    :class="{ 'uat-button-small': size === 'small' }"
    :type="type"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<style scoped>
.uat-button-primary {
  border-color: #e0a500;
  color: #5c3b00;
  background: #f5b700;
}

.uat-button-primary:hover:not(:disabled) {
  background: #f6b902;
}
</style>
