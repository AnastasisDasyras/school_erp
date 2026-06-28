<script setup lang="ts">
defineProps<{
  modelValue: string;
  label: string;
  type?: string;
  required?: boolean;
}>();

defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <label class="block text-sm">
    <span class="text-gray-700">{{ label }}</span>
    <input
      :type="type ?? 'text'"
      :value="modelValue"
      :required="required"
      class="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm px-2 py-1.5 focus:border-blue-500 focus:ring-blue-500"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
  </label>
</template>
