import { apiClient } from "@/api/client";
import type { CreateStudentPayload, Student, StudentPage, UpdateStudentPayload } from "@/types/student";

/**
 * Typed API service — the only layer that knows about HTTP/Axios.
 * Stores call these functions; they never call axios directly.
 */
export const studentsApi = {
  async list(params: { offset?: number; limit?: number; search?: string }): Promise<StudentPage> {
    const { data } = await apiClient.get<StudentPage>("/students", { params });
    return data;
  },

  async get(id: string): Promise<Student> {
    const { data } = await apiClient.get<Student>(`/students/${id}`);
    return data;
  },

  async create(payload: CreateStudentPayload): Promise<Student> {
    const { data } = await apiClient.post<Student>("/students", payload);
    return data;
  },

  async update(id: string, payload: UpdateStudentPayload): Promise<Student> {
    const { data } = await apiClient.put<Student>(`/students/${id}`, payload);
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/students/${id}`);
  },
};
