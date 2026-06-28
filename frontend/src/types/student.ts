export interface Student {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  date_of_birth: string;
  enrolled_on: string;
  is_active: boolean;
}

export interface StudentPage {
  items: Student[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateStudentPayload {
  first_name: string;
  last_name: string;
  email: string;
  date_of_birth: string;
}

export type UpdateStudentPayload = CreateStudentPayload;
