import { apiClient } from "@/lib/api/client";

export interface CrmPipelineStage {
  stage: string;
  opportunity_count: number;
  pipeline_amount: number;
  weighted_amount: number;
}

export interface CrmOpportunity {
  id: string;
  name: string;
  stage: string;
  amount: number;
  probability: number;
  expected_close_date: string | null;
  status: string;
  next_action: string | null;
  weighted_amount: number;
  days_to_close: number | null;
}

export interface CrmWorkItem {
  id: string;
  source: string;
  created_date?: string;
  received_date?: string;
  due_date: string | null;
  status: string;
  estimated_value: number;
  age_days: number | null;
  overdue: boolean;
  priority?: string;
}

export interface CrmWorkSummaryRow {
  work_type: string;
  status: string;
  item_count: number;
  estimated_value: number;
}

export interface CrmActivity {
  activity_id: string;
  activity_type: string | null;
  activity_date: string | null;
  status: string | null;
  subject: string | null;
  with: string | null;
  notes_summary: string | null;
  next_action: string | null;
  next_action_date: string | null;
  sentiment: string | null;
}

export interface CrmActivitiesData {
  activities: CrmActivity[];
  by_type: Record<string, number>;
  this_week: Record<string, number>;
  recent_meetings: CrmActivity[];
  upcoming: CrmActivity[];
}

const unwrap = <T,>(key: string, obj: Record<string, unknown>): T => (obj?.[key] ?? []) as T;

export async function fetchCrmActivities(advisorId: string): Promise<CrmActivitiesData> {
  return apiClient.get<CrmActivitiesData>(`/crm/activities/${advisorId}`);
}

export async function fetchCrmPipeline(advisorId: string): Promise<CrmPipelineStage[]> {
  const d = await apiClient.get<Record<string, unknown>>(`/crm/pipeline/${advisorId}`);
  return unwrap<CrmPipelineStage[]>("pipeline_by_stage", d);
}
export async function fetchCrmOpportunities(advisorId: string): Promise<CrmOpportunity[]> {
  const d = await apiClient.get<Record<string, unknown>>(`/crm/opportunities/${advisorId}`);
  return unwrap<CrmOpportunity[]>("opportunities", d);
}
export async function fetchCrmLeads(advisorId: string): Promise<CrmWorkItem[]> {
  const d = await apiClient.get<Record<string, unknown>>(`/crm/leads/${advisorId}`);
  return unwrap<CrmWorkItem[]>("leads", d);
}
export async function fetchCrmReferrals(advisorId: string): Promise<CrmWorkItem[]> {
  const d = await apiClient.get<Record<string, unknown>>(`/crm/referrals/${advisorId}`);
  return unwrap<CrmWorkItem[]>("referrals", d);
}
export async function fetchCrmWorkSummary(advisorId: string): Promise<CrmWorkSummaryRow[]> {
  const d = await apiClient.get<Record<string, unknown>>(`/crm/work-summary/${advisorId}`);
  return unwrap<CrmWorkSummaryRow[]>("work_summary", d);
}
