<script setup lang="ts">
import BaseButton from "@/components/base/BaseButton.vue";
import type { Student } from "@/types/student";

// Humble component: props in, events out. No store access, no API calls.
defineProps<{
  students: Student[];
  isLoading: boolean;
}>();

defineEmits<{
  edit: [student: Student];
  delete: [student: Student];
}>();
</script>

<template>
  <table class="w-full text-sm border rounded overflow-hidden bg-white">
    <thead class="bg-gray-100 text-left text-gray-600">
      <tr>
        <th class="px-3 py-2">Name</th>
        <th class="px-3 py-2">Email</th>
        <th class="px-3 py-2">Date of birth</th>
        <th class="px-3 py-2">Status</th>
        <th class="px-3 py-2"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-if="isLoading">
        <td colspan="5" class="px-3 py-4 text-center text-gray-400">Loading…</td>
      </tr>
      <tr v-else-if="students.length === 0">
        <td colspan="5" class="px-3 py-4 text-center text-gray-400">No students found</td>
      </tr>
      <tr v-for="student in students" :key="student.id" class="border-t">
        <td class="px-3 py-2">{{ student.full_name }}</td>
        <td class="px-3 py-2">{{ student.email }}</td>
        <td class="px-3 py-2">{{ student.date_of_birth }}</td>
        <td class="px-3 py-2">
          <span :class="student.is_active ? 'text-green-600' : 'text-gray-400'">
            {{ student.is_active ? "Active" : "Inactive" }}
          </span>
        </td>
        <td class="px-3 py-2 text-right space-x-2">
          <BaseButton variant="ghost" @click="$emit('edit', student)">Edit</BaseButton>
          <BaseButton variant="danger" @click="$emit('delete', student)">Delete</BaseButton>
        </td>
      </tr>
    </tbody>
  </table>
</template>
