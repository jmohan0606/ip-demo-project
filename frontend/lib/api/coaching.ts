import { apiClient } from "@/lib/api/client";

export interface UserRef {
  user_id: string | null;
  display_name: string | null;
  role_code: string | null;
}

export interface CoachingSession {
  session_id: string;
  session_date: string | null;
  session_type: string | null;
  coach_user_id: string | null;
  coach?: UserRef;
  status: string | null;
  summary: string | null;
  action_items: string[];
  next_session_date: string | null;
}

export interface ManagerReview {
  review_id: string;
  review_date: string | null;
  review_type: string | null;
  reviewer_user_id: string | null;
  reviewer?: UserRef;
  rating: number | null;
  status: string | null;
  summary: string | null;
}

export interface CoachingTask {
  task_id: string;
  title: string | null;
  category: string | null;
  instruction: string | null;
  status: string;
  priority: string | null;
  created_date: string | null;
  due_date: string | null;
  completed_date: string | null;
  assigned_by: UserRef | null;
}

export interface TaskTemplate {
  title: string; category: string; instruction: string; priority: string;
}

export interface CoachingReviewData {
  advisor_id: string;
  advisor_name: string;
  coaching_sessions: CoachingSession[];
  manager_reviews: ManagerReview[];
  summary: {
    session_count: number;
    review_count: number;
    avg_rating: number | null;
    open_action_items: number;
    total_action_items: number;
  };
  evidence: { source: string };
}

export async function fetchCoaching(advisorId: string): Promise<CoachingReviewData> {
  return apiClient.get<CoachingReviewData>(`/coaching/advisor/${advisorId}`);
}

export async function fetchTaskCatalog(): Promise<TaskTemplate[]> {
  const d = await apiClient.get<{ catalog: TaskTemplate[] }>(`/coaching/task-catalog`);
  return d.catalog ?? [];
}

export async function fetchCoachingTasks(advisorId: string): Promise<{ tasks: CoachingTask[]; open_count: number; total: number }> {
  return apiClient.get<{ tasks: CoachingTask[]; open_count: number; total: number }>(`/coaching/tasks/${advisorId}`);
}

export async function createCoachingTask(body: {
  advisor_id: string; title: string; category: string; instruction: string; priority: string; due_date?: string | null; created_date?: string | null;
}): Promise<{ task_id: string }> {
  return apiClient.post<{ task_id: string }>(`/coaching/tasks`, body);
}

export async function updateCoachingTaskStatus(taskId: string, status: string, completed_date?: string | null): Promise<{ updated: boolean }> {
  return apiClient.patch<{ updated: boolean }>(`/coaching/tasks/${taskId}/status`, { status, completed_date });
}
