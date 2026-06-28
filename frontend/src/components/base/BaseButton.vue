<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: "primary" | "danger" | "ghost";
    type?: "button" | "submit";
  }>(),
  { variant: "primary", type: "button" },
);

defineEmits<{ click: [] }>();

const variantClasses: Record<string, string> = {
  primary: "bg-blue-600 text-white hover:bg-blue-700",
  danger: "bg-red-600 text-white hover:bg-red-700",
  ghost: "bg-transparent text-gray-700 hover:bg-gray-100",
};
</script>

<template>
  <button
    :type="type"
    class="px-3 py-1.5 rounded text-sm font-medium transition-colors"
    :class="variantClasses[variant]"
    @click="$emit('click')"
  >
    <slot />
  </button>
</template>
