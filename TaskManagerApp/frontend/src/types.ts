export type TaskStatus =
  | "pending"
  | "acknowledged"
  | "rejected"
  | "completed"
  | "failed";

export const TASK_STATUSES: TaskStatus[] = [
  "pending",
  "acknowledged",
  "rejected",
  "completed",
  "failed",
];

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  manager_id: number | null;
}

export interface Task {
  id: number;
  title: string;
  description: string;
  deadline: string; // YYYY-MM-DD
  status: TaskStatus;
  assigned_user_id: number;
  created_by: number;
  created_at: string;
  updated_at: string;
  creator_name: string;
  assigned_user_name: string;
  comment_count: number;
  can_edit: boolean;
}

export interface Comment {
  id: number;
  task_id: number;
  content: string;
  created_by: number;
  created_at: string;
  author: string;
}

export interface TaskFilters {
  sort?: "created" | "deadline";
  status?: TaskStatus;
  created_by?: number;
  assigned_to?: number;
  managed?: "created" | "assigned";
}
