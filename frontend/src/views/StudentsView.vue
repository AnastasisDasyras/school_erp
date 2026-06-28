<script setup lang="ts">
import { onMounted, ref } from "vue";

import BaseButton from "@/components/base/BaseButton.vue";
import StudentForm from "@/components/students/StudentForm.vue";
import StudentsTable from "@/components/students/StudentsTable.vue";
import { useStudents } from "@/composables/useStudents";
import type { CreateStudentPayload, Student } from "@/types/student";

// "Smart" view: wires the composable (which wraps the store) to humble components.
const {
  students,
  total,
  isLoading,
  error,
  page,
  pageCount,
  load,
  search,
  goToPage,
  createStudent,
  updateStudent,
  deleteStudent,
} = useStudents();

const isFormOpen = ref(false);
const editingStudent = ref<Student | null>(null);
const searchTerm = ref("");

onMounted(load);

function openCreateForm(): void {
  editingStudent.value = null;
  isFormOpen.value = true;
}

function openEditForm(student: Student): void {
  editingStudent.value = student;
  isFormOpen.value = true;
}

async function onSubmit(payload: CreateStudentPayload): Promise<void> {
  if (editingStudent.value) {
    await updateStudent(editingStudent.value.id, payload);
  } else {
    await createStudent(payload);
  }
  isFormOpen.value = false;
}

async function onDelete(student: Student): Promise<void> {
  await deleteStudent(student.id);
}

async function onSearch(): Promise<void> {
  await search(searchTerm.value);
}
</script>

<template>
  <div class="space-y-4 max-w-4xl">
    <div class="flex items-center justify-between">
      <h2 class="text-base font-semibold text-gray-900">Students ({{ total }})</h2>
      <BaseButton @click="openCreateForm">Add student</BaseButton>
    </div>

    <input
      v-model="searchTerm"
      placeholder="Search by name or email…"
      class="block w-full max-w-sm rounded border-gray-300 shadow-sm text-sm px-2 py-1.5"
      @keyup.enter="onSearch"
    />

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

    <StudentsTable
      :students="students"
      :is-loading="isLoading"
      @edit="openEditForm"
      @delete="onDelete"
    />

    <div class="flex justify-end gap-2 text-sm">
      <BaseButton variant="ghost" :disabled="page <= 1" @click="goToPage(page - 1)">Prev</BaseButton>
      <span class="px-2 py-1">{{ page }} / {{ pageCount }}</span>
      <BaseButton variant="ghost" :disabled="page >= pageCount" @click="goToPage(page + 1)">Next</BaseButton>
    </div>

    <div v-if="isFormOpen" class="fixed inset-0 bg-black/30 flex items-center justify-center">
      <div class="w-full max-w-sm">
        <StudentForm :initial="editingStudent" @submit="onSubmit" @cancel="isFormOpen = false" />
      </div>
    </div>
  </div>
</template>
