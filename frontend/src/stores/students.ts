import { defineStore } from "pinia";

import { studentsApi } from "@/api/students";
import type { CreateStudentPayload, Student, UpdateStudentPayload } from "@/types/student";

interface StudentsState {
  items: Student[];
  total: number;
  offset: number;
  limit: number;
  search: string;
  isLoading: boolean;
  error: string | null;
}

export const useStudentsStore = defineStore("students", {
  state: (): StudentsState => ({
    items: [],
    total: 0,
    offset: 0,
    limit: 20,
    search: "",
    isLoading: false,
    error: null,
  }),

  actions: {
    async fetchPage(): Promise<void> {
      this.isLoading = true;
      this.error = null;
      try {
        const page = await studentsApi.list({
          offset: this.offset,
          limit: this.limit,
          search: this.search || undefined,
        });
        this.items = page.items;
        this.total = page.total;
      } catch (err) {
        this.error = "Failed to load students";
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async create(payload: CreateStudentPayload): Promise<void> {
      await studentsApi.create(payload);
      await this.fetchPage();
    },

    async update(id: string, payload: UpdateStudentPayload): Promise<void> {
      await studentsApi.update(id, payload);
      await this.fetchPage();
    },

    async remove(id: string): Promise<void> {
      await studentsApi.remove(id);
      await this.fetchPage();
    },

    setSearch(search: string): void {
      this.search = search;
      this.offset = 0;
    },

    setPage(offset: number): void {
      this.offset = offset;
    },
  },
});
