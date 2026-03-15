// src/components/tasks/TaskForm.tsx
import { useState } from 'react'
import type { Experience, TaskCreate, TaskStatus } from '../../types'
import { formatExperienceName } from '../../utils/formatters'
import styles from './TaskForm.module.css'

interface TaskFormProps {
  initialValues?: Partial<TaskCreate>
  experiences: Experience[]
  onSubmit: (values: TaskCreate) => void
  onCancel: () => void
  error?: string
  isLoading?: boolean
}

const STATUS_OPTIONS: { value: TaskStatus; label: string }[] = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'done', label: 'Done' },
]


export default function TaskForm({
  initialValues = {},
  experiences,
  onSubmit,
  onCancel,
  error,
  isLoading,
}: TaskFormProps) {
  const [title, setTitle] = useState(initialValues.title ?? '')
  const [description, setDescription] = useState(initialValues.description ?? '')
  const [status, setStatus] = useState<TaskStatus>(initialValues.status ?? 'todo')
  const [experienceId, setExperienceId] = useState<string>(
    initialValues.experience_id != null ? String(initialValues.experience_id) : ''
  )
  const [dueAt, setDueAt] = useState(
    initialValues.due_at ? initialValues.due_at.slice(0, 10) : ''
  )
  const [titleError, setTitleError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) {
      setTitleError('Title is required')
      return
    }
    setTitleError('')

    const values: TaskCreate = {
      title: title.trim(),
      description: description.trim() || undefined,
      status,
      experience_id: experienceId ? Number(experienceId) : undefined,
      // Convert local date string to ISO datetime (end of day UTC, preserving selected date)
      due_at: dueAt ? dueAt + 'T23:59:59Z' : undefined,
    }
    onSubmit(values)
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="tf-title">Title *</label>
        <input
          id="tf-title"
          className={`${styles.input} ${titleError ? styles.inputError : ''}`}
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Task title"
          autoFocus
        />
        {titleError && <div className={styles.fieldError}>{titleError}</div>}
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="tf-desc">Description</label>
        <textarea
          id="tf-desc"
          className={`${styles.input} ${styles.textarea}`}
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Optional description"
          rows={3}
        />
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="tf-status">Status</label>
        <select
          id="tf-status"
          className={styles.select}
          value={status}
          onChange={e => setStatus(e.target.value as TaskStatus)}
        >
          {STATUS_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className={styles.row}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="tf-exp">Experience</label>
          <select
            id="tf-exp"
            className={styles.select}
            value={experienceId}
            onChange={e => setExperienceId(e.target.value)}
          >
            <option value="">— None —</option>
            {experiences.map(exp => (
              <option key={exp.id} value={String(exp.id)}>
                {formatExperienceName(exp.folder_path)}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="tf-due">Due date</label>
          <input
            id="tf-due"
            className={styles.input}
            type="date"
            value={dueAt}
            onChange={e => setDueAt(e.target.value)}
          />
        </div>
      </div>

      {error && <div className={styles.formError}>{error}</div>}

      <div className={styles.actions}>
        <button type="button" className={styles.cancelBtn} onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className={styles.submitBtn} disabled={isLoading}>
          {isLoading ? 'Saving…' : 'Save task'}
        </button>
      </div>
    </form>
  )
}
