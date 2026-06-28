<script setup lang="ts">
import { reactive, watch } from "vue";

import BaseButton from "@/components/base/BaseButton.vue";
import BaseInput from "@/components/base/BaseInput.vue";
import type { CreateStudentPayload, Student } from "@/types/student";

// Humble component: holds only local form state, emits the result upward.
const props = defineProps<{
  initial?: Student | null;
}>();

const emit = defineEmits<{
  submit: [payload: CreateStudentPayload];
  cancel: [];
}>();

const form = reactive<CreateStudentPayload>({
  first_name: "",
  last_name: "",
  email: "",
  date_of_birth: "",
});

watch(
  () => props.initial,
  (student) => {
    form.first_name = student?.first_name ?? "";
    form.last_name = student?.last_name ?? "";
    form.email = student?.email ?? "";
    form.date_of_birth = student?.date_of_birth ?? "";
  },
  { immediate: true },
);

function onSubmit(): void {
  emit("submit", { ...form });
}
</script>

<template>
  <form class="space-y-3 bg-white p-4 rounded border" @submit.prevent="onSubmit">
    <BaseInput v-model="form.first_name" label="First name" required />
    <BaseInput v-model="form.last_name" label="Last name" required />
    <BaseInput v-model="form.email" label="Email" type="email" required />
    <BaseInput v-model="form.date_of_birth" label="Date of birth" type="date" required />
    <div class="flex justify-end gap-2">
      <BaseButton variant="ghost" @click="$emit('cancel')">Cancel</BaseButton>
      <BaseButton type="submit">Save</BaseButton>
    </div>
  </form>
</template>
