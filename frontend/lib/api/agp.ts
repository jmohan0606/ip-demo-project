import { apiClient } from "@/lib/api/client";

export interface AgpTrackStatus {
  advisor_id: string;
  enrolled: boolean;
  enrollment_id: string | null;
  score: number;
  band: string;
  severity: string;
  components: {
    attainment_gap: number;
    time_pressure: number;
    crm_execution_risk: number;
    weights: Record<string, number>;
  };
  explanation: string;
  current_milestone: {
    milestone_progress_id: string;
    due_date: string;
    days_remaining: number;
    status: string;
    attainment_pct: number;
    risk_score: number;
  } | null;
}

export interface AgpEnrollment {
  enrollment_id: string;
  cohort: string;
  status: string;
  start_date: string;
  expected_end_date: string;
  current_program_month: number;
  months_elapsed: number;
  months_remaining: number;
}

export interface AgpCohortSummary {
  program_id: string;
  cohort: string;
  scope: { scope_type: string; scope_id: string };
  enrollment_count: number;
  milestone_summary: Array<{
    milestone_status: string;
    progress_count: number;
    avg_attainment_pct: number;
    avg_risk_score: number;
  }>;
}

export interface AgpCoachingSession {
  session_id: string;
  session_date: string | null;
  session_type: string | null;
  status: string | null;
  summary: string | null;
  action_items_json?: string | null;
  coach_user_id?: string | null;
}

export interface AgpKpiHistoryPoint {
  label: string; month: number; target: number; actual: number; attainment_pct: number; status: string | null; measured_at: string | null;
}
export interface AgpKpiRow {
  kpi_id: string; kpi_name: string; unit: string | null; direction: string | null;
  target: number | null; current: number | null; attainment_pct: number; status: string | null;
  history: AgpKpiHistoryPoint[];
}
export async function fetchAgpKpiScorecard(advisorId: string): Promise<{ scorecard: AgpKpiRow[] }> {
  return apiClient.get<{ scorecard: AgpKpiRow[] }>(`/agp/kpi-scorecard/${advisorId}`);
}

export async function fetchAgpTrackStatus(advisorId: string): Promise<AgpTrackStatus> {
  return apiClient.get<AgpTrackStatus>(`/agp/track-status/${advisorId}`);
}
export async function fetchAgpEnrollment(advisorId: string): Promise<{ enrollments: AgpEnrollment[] }> {
  return apiClient.get<{ enrollments: AgpEnrollment[] }>(`/agp/enrollment/${advisorId}`);
}
export async function fetchAgpCohortSummary(scopeType: string, scopeId: string): Promise<AgpCohortSummary> {
  return apiClient.get<AgpCohortSummary>(
    `/agp/cohort-summary?scope_type=${encodeURIComponent(scopeType)}&scope_id=${encodeURIComponent(scopeId)}`,
  );
}
export async function fetchAgpCoaching(advisorId: string): Promise<{ coaching_sessions: AgpCoachingSession[] }> {
  return apiClient.get<{ coaching_sessions: AgpCoachingSession[] }>(`/agp/coaching/${advisorId}`);
}
