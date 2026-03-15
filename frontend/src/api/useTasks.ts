// src/api/useTasks.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Task, TaskCreate, TaskUpdate, TaskStatus } from '../types'

export interface TaskFilters {
  status?: TaskStatus[]
  experience_id?: number
  updated_after?: string
  updated_before?: string
}

async function fetchTasks(filters: TaskFilters = {}): Promise<Task[]> {
  const params = new URLSearchParams()
  if (filters.status) {
    filters.status.forEach(s => params.append('status', s))
  }
  if (filters.experience_id != null) {
    params.set('experience_id', String(filters.experience_id))
  }
  if (filters.updated_after) params.set('updated_after', filters.updated_after)
  if (filters.updated_before) params.set('updated_before', filters.updated_before)

  const qs = params.toString()
  const res = await fetch(`/api/tasks${qs ? '?' + qs : ''}`)
  if (!res.ok) throw new Error(`Failed to fetch tasks: ${res.status}`)
  return res.json()
}

export function useTasks(filters: TaskFilters = {}) {
  return useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => fetchTasks(filters),
  })
}

export function useCreateTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: TaskCreate): Promise<Task> => {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(`Failed to create task: ${res.status}`)
      return res.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
}

export function useUpdateTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...body }: { id: number } & TaskUpdate): Promise<Task> => {
      const res = await fetch(`/api/tasks/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(`Failed to update task: ${res.status}`)
      return res.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
}

export function useCompleteTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      time_spent_minutes,
    }: {
      id: number
      time_spent_minutes?: number
    }): Promise<Task> => {
      const res = await fetch(`/api/tasks/${id}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_spent_minutes }),
      })
      if (!res.ok) throw new Error(`Failed to complete task: ${res.status}`)
      return res.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
}

export function useUncompleteTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number): Promise<Task> => {
      const res = await fetch(`/api/tasks/${id}/uncomplete`, { method: 'POST' })
      if (!res.ok) throw new Error(`Failed to uncomplete task: ${res.status}`)
      return res.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
}
