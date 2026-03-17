// src/types/index.ts
export type TaskStatus = "todo" | "in_progress" | "blocked" | "done" | "cancelled";

export interface Task {
  id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  experience_id: number | null;
  due_at: string | null; // ISO datetime string
  created_at: string;
  updated_at: string;
  parent_task_id: number | null;
  created_by: string;
  external_ref: string | null;
  time_spent_minutes: number | null;
  last_activity_at: string; // ISO datetime string
}

export interface Experience {
  id: number;
  active: boolean;
  folder_path: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  status?: TaskStatus;
  experience_id?: number;
  due_at?: string; // ISO datetime string
  parent_task_id?: number;
  external_ref?: string;
}

// Matches spec exactly: all TaskCreate fields are optional in an update, including title
export interface TaskUpdate extends Partial<Omit<TaskCreate, "title">> {
  title?: string;
}

export type ProposalType = "create_task" | "update_task" | "change_status" | "cancel_task";
export type ProposalStatus = "pending" | "approved" | "rejected" | "superseded";

export interface IngestionRunSummary {
  id: number;
  started_at: string;
  status: string;
  triggered_by: string;
  range_start: string | null;
  range_end: string | null;
}

export interface IngestionBatchSummary {
  id: number;
  source_type: string;
  status: string;
  item_count: number | null;
  ingestion_run: IngestionRunSummary | null;
}

export interface TaskSummary {
  id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  experience_id: number | null;
  due_at: string | null;
  external_ref: string | null;
}

export interface TaskProposal {
  id: number;
  proposal_type: ProposalType;
  status: ProposalStatus;
  task_id: number | null;
  proposed_title: string | null;
  proposed_description: string | null;
  proposed_status: TaskStatus | null;
  proposed_experience_id: number | null;
  proposed_due_at: string | null;
  proposed_parent_task_id: number | null;
  proposed_external_ref: string | null;
  reason_summary: string | null;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  created_by: string;
  ingestion_batch_id: number | null;
  task: TaskSummary | null;
  ingestion_batch: IngestionBatchSummary | null;
}

export interface ApproveProposalRequest {
  proposed_title?: string;
  proposed_description?: string;
  proposed_status?: TaskStatus;
  proposed_experience_id?: number;
  proposed_due_at?: string;
  proposed_external_ref?: string;
}
