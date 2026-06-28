import { computed } from "vue";

import { useStudentsStore } from "@/stores/students";
import type { CreateStudentPayload, UpdateStudentPayload } from "@/types/student";

/**
 * Composable: the seam between "smart" views and the Pinia store.
 * Views call these functions; they never read/write store state directly,
 * which keeps the store free to evolve independently of any one view.
 */
export function useStudents() {
  const store = useStudentsStore();

  const students = computed(() => store.items);
  const total = computed(() => store.total);
  const isLoading = computed(() => store.isLoading);
  const error = computed(() => store.error);
  const page = computed(() => Math.floor(store.offset / store.limit) + 1);
  const pageCount = computed(() => Math.max(1, Math.ceil(store.total / store.limit)));

  async function load(): Promise<void> {
    await store.fetchPage();
  }

  async function search(term: string): Promise<void> {
    store.setSearch(term);
    await store.fetchPage();
  }

  async function goToPage(targetPage: number): Promise<void> {
    store.setPage((targetPage - 1) * store.limit);
    await store.fetchPage();
  }

  async function createStudent(payload: CreateStudentPayload): Promise<void> {
    await store.create(payload);
  }

  async function updateStudent(id: string, payload: UpdateStudentPayload): Promise<void> {
    await store.update(id, payload);
  }

  async function deleteStudent(id: string): Promise<void> {
    await store.remove(id);
  }

  return {
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
  };
}
