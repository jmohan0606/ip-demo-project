import { apiClient } from "@/lib/api/client";

export interface CoachingSession {
  session_id: string;
  session_date: string | null;
  session_type: string | null;
  coach_user_id: string | null;
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
  rating: number | null;
  status: string | null;
  summary: string | null;
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
