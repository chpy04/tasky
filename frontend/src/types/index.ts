// src/types/index.ts
export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'done' | 'cancelled'

export interface Task {
  id: number
  title: string
  description: string | null
  status: TaskStatus
  experience_id: number | null
  due_at: string | null        // ISO datetime string
  created_at: string
  updated_at: string
  parent_task_id: number | null
  created_by: string
  external_ref: string | null
  time_spent_minutes: number | null
  last_activity_at: string     // ISO datetime string
}

export interface Experience {
  id: number
  active: boolean
  folder_path: string
}

export interface TaskCreate {
  title: string
  description?: string
  status?: TaskStatus
  experience_id?: number
  due_at?: string              // ISO datetime string
  parent_task_id?: number
  external_ref?: string
}

// Matches spec exactly: all TaskCreate fields are optional in an update, including title
export interface TaskUpdate extends Partial<Omit<TaskCreate, 'title'>> {
  title?: string
}
