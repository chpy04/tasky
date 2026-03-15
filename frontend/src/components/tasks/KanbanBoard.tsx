// src/components/tasks/KanbanBoard.tsx
import { useEffect, useRef, useState } from 'react'
import { useCreateTask, useUpdateTask, useCompleteTask, useUncompleteTask } from '../../api/useTasks'
import { useExperiences } from '../../api/useExperiences'
import type { Experience, Task, TaskCreate, TaskStatus } from '../../types'
import { getExperienceColor } from '../../theme'
import { formatExperienceName, isDueSoon, isWithinLastDays } from '../../utils/formatters'
import FilterChip from '../ui/FilterChip'
import Modal from '../ui/Modal'
import TaskColumn from './TaskColumn'
import TaskForm from './TaskForm'
import styles from './KanbanBoard.module.css'

const COLUMN_ORDER: TaskStatus[] = ['todo', 'in_progress', 'done']


interface KanbanBoardProps {
  tasks: Task[]
  showCreateModal: boolean
  onCloseCreateModal: () => void
}

export default function KanbanBoard({ tasks, showCreateModal, onCloseCreateModal }: KanbanBoardProps) {
  const [selectedExperienceIds, setSelectedExperienceIds] = useState<Set<number> | null>(null)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [uncompleteTaskId, setUncompleteTaskId] = useState<number | null>(null)
  // toastError: background mutation errors (complete/statusChange) shown as a banner
  const [toastError, setToastError] = useState<string | null>(null)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Clear toast timer on unmount to avoid setState on an unmounted component
  useEffect(() => {
    return () => {
      if (toastTimerRef.current != null) clearTimeout(toastTimerRef.current)
    }
  }, [])

  const { data: experiences = [] } = useExperiences()
  const createTask = useCreateTask()
  const updateTask = useUpdateTask()
  const completeTask = useCompleteTask()
  const uncompleteTask = useUncompleteTask()

  function toggleExperience(id: number) {
    setSelectedExperienceIds(prev => {
      const next = new Set(prev ?? [])
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      // If nothing is selected, revert to "All"
      return next.size === 0 ? null : next
    })
  }

  // Client-side filtering — cancelled check first (cheapest, always excluded)
  const filtered = tasks.filter(t => {
    if (t.status === 'cancelled') return false
    if (selectedExperienceIds !== null && (t.experience_id == null || !selectedExperienceIds.has(t.experience_id))) return false
    return true
  })

  function sortByDueAsc(tasks: Task[]): Task[] {
    return [...tasks].sort((a, b) => {
      if (a.due_at == null && b.due_at == null) return 0
      if (a.due_at == null) return 1
      if (b.due_at == null) return -1
      return a.due_at < b.due_at ? -1 : a.due_at > b.due_at ? 1 : 0
    })
  }

  function sortByActivityDesc(tasks: Task[]): Task[] {
    return [...tasks].sort((a, b) =>
      a.last_activity_at > b.last_activity_at ? -1 : a.last_activity_at < b.last_activity_at ? 1 : 0
    )
  }

  function getColumnTasks(status: TaskStatus) {
    if (status === 'todo') {
      // Blocked tasks appear in To Do with a red outline
      // todo tasks due within 3 days are promoted to In Progress display
      const active = sortByDueAsc(filtered.filter(t =>
        (t.status === 'todo' && !isDueSoon(t.due_at)) || t.status === 'blocked'
      ))
      return { active, done: [] }
    }
    if (status === 'in_progress') {
      // In Progress shows true in_progress tasks + todo tasks due within 3 days
      const active = sortByDueAsc(filtered.filter(t =>
        t.status === 'in_progress' || (t.status === 'todo' && isDueSoon(t.due_at))
      ))
      return { active, done: [] }
    }
    if (status === 'done') {
      const active = sortByActivityDesc(
        filtered.filter(t => t.status === 'done' && isWithinLastDays(t.last_activity_at, 7))
      )
      return { active, done: [] }
    }
    return { active: filtered.filter(t => t.status === status), done: [] }
  }

  // Create/update errors are shown inline in TaskForm via the mutation's isError state.
  // Complete/statusChange errors are shown as the toast banner (toastError) with auto-clear.
  async function handleCreate(values: TaskCreate) {
    try {
      await createTask.mutateAsync(values)
      closeCreateModal()  // calls reset() to clear any stale error state
    } catch {
      // Error shown via createTask.isError prop passed to TaskForm
    }
  }

  async function handleUpdate(values: TaskCreate) {
    if (!editingTask) return
    try {
      await updateTask.mutateAsync({ id: editingTask.id, ...values })
      setEditingTask(null)
    } catch {
      // Error shown via updateTask.isError prop passed to TaskForm
    }
  }

  function closeCreateModal() {
    onCloseCreateModal()
    createTask.reset()   // clear any stale error state
  }

  function closeEditModal() {
    setEditingTask(null)
    updateTask.reset()
  }

  async function handleComplete(id: number) {
    try {
      await completeTask.mutateAsync({ id })
    } catch {
      setToastError('Failed to mark task complete. Please try again.')
      if (toastTimerRef.current != null) clearTimeout(toastTimerRef.current)
      toastTimerRef.current = setTimeout(() => setToastError(null), 4000)
    }
  }

  async function handleConfirmUncomplete() {
    if (uncompleteTaskId == null) return
    const id = uncompleteTaskId
    setUncompleteTaskId(null)
    try {
      await uncompleteTask.mutateAsync(id)
    } catch {
      setToastError('Failed to undo task completion. Please try again.')
      if (toastTimerRef.current != null) clearTimeout(toastTimerRef.current)
      toastTimerRef.current = setTimeout(() => setToastError(null), 4000)
    }
  }

  async function handleStatusChange(id: number, status: TaskStatus) {
    try {
      await updateTask.mutateAsync({ id, status })
    } catch {
      setToastError('Failed to update task status. Please try again.')
      if (toastTimerRef.current != null) clearTimeout(toastTimerRef.current)
      toastTimerRef.current = setTimeout(() => setToastError(null), 4000)
    }
  }

  const activeExperiences = experiences.filter(e => e.active)

  // Count visible tasks per experience (respecting status filter, ignoring experience filter)
  const visibleTasks = tasks.filter(t => t.status !== 'cancelled')
  const taskCountByExperience = (expId: number) =>
    visibleTasks.filter(t => t.experience_id === expId).length
  const sortedActiveExperiences = [...activeExperiences].sort(
    (a, b) => taskCountByExperience(b.id) - taskCountByExperience(a.id)
  )

  return (
    <div className={styles.board}>
      {/* Filter bar */}
      <div className={styles.filterBar}>
        <div className={styles.filterGroup}>
          <span className={styles.filterLabel}>Experience</span>
          <div className={styles.chips}>
            <FilterChip
              label="All"
              active={selectedExperienceIds === null}
              onClick={() => setSelectedExperienceIds(null)}
            />
            {sortedActiveExperiences.map(exp => (
              <FilterChip
                key={exp.id}
                label={formatExperienceName(exp.folder_path)}
                active={selectedExperienceIds !== null && selectedExperienceIds.has(exp.id)}
                onClick={() => toggleExperience(exp.id)}
                dot={getExperienceColor(exp.id)}
              />
            ))}
          </div>
        </div>

      </div>

      {/* Toast error banner (background mutations: complete, statusChange) */}
      {toastError && (
        <div className={styles.errorBanner}>
          {toastError}
          <button className={styles.errorClose} onClick={() => setToastError(null)}>✕</button>
        </div>
      )}

      {/* Columns */}
      <div className={styles.columns}>
        {COLUMN_ORDER.map(status => {
          const { active, done } = getColumnTasks(status)
          return (
            <TaskColumn
              key={status}
              status={status}
              activeTasks={active}
              doneTasks={done}
              experiences={experiences}
              onEdit={setEditingTask}
              onComplete={handleComplete}
              onUncomplete={setUncompleteTaskId}
              onStatusChange={handleStatusChange}
            />
          )
        })}
      </div>

      {/* Uncomplete confirmation modal */}
      {uncompleteTaskId != null && (
        <Modal
          title="Undo completion?"
          onClose={() => setUncompleteTaskId(null)}
          actions={[
            { label: 'Cancel', variant: 'ghost', onClick: () => setUncompleteTaskId(null) },
            { label: 'Undo completion', variant: 'danger', onClick: handleConfirmUncomplete },
          ]}
        >
          <p>This will mark the task as incomplete and restore its previous status.</p>
        </Modal>
      )}

      {/* Create modal — inline error shown via createTask.isError */}
      {showCreateModal && (
        <Modal title="New task" onClose={closeCreateModal}>
          <TaskForm
            experiences={activeExperiences}
            onSubmit={handleCreate}
            onCancel={closeCreateModal}
            error={createTask.isError ? 'Failed to create task. Please try again.' : undefined}
            isLoading={createTask.isPending}
          />
        </Modal>
      )}

      {/* Edit modal — inline error shown via updateTask.isError */}
      {editingTask && (
        <Modal title="Edit task" onClose={closeEditModal}>
          <TaskForm
            initialValues={{
              title: editingTask.title,
              description: editingTask.description ?? undefined,
              status: editingTask.status,
              experience_id: editingTask.experience_id ?? undefined,
              due_at: editingTask.due_at ?? undefined,
            }}
            experiences={activeExperiences}
            onSubmit={handleUpdate}
            onCancel={closeEditModal}
            error={updateTask.isError ? 'Failed to update task. Please try again.' : undefined}
            isLoading={updateTask.isPending}
          />
        </Modal>
      )}
    </div>
  )
}
