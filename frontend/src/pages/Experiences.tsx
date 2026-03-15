// src/pages/Experiences.tsx
import { useState } from 'react'
import { useExperiences, useCreateExperience, useDeactivateExperience } from '../api/useExperiences'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import { formatExperienceName } from '../utils/formatters'
import { getExperienceColor } from '../theme'
import type { Experience } from '../types'
import styles from './Experiences.module.css'

function ExperienceCard({ exp }: { exp: Experience }) {
  const [confirming, setConfirming] = useState(false)
  const deactivate = useDeactivateExperience()
  const activate = useCreateExperience()

  const handleConfirmDeactivate = () => {
    deactivate.mutate(exp.id, { onSettled: () => setConfirming(false) })
  }

  const accentColor = getExperienceColor(exp.id)
  const mutationError = deactivate.isError
    ? (deactivate.error as Error).message
    : activate.isError
    ? (activate.error as Error).message
    : null

  return (
    <div className={styles.card} style={{ borderLeftColor: accentColor }}>
      <div className={styles.cardMain}>
        <span className={styles.cardName}>{formatExperienceName(exp.folder_path)}</span>
        <span
          className={styles.badge}
          style={{ color: exp.active ? '#72a848' : '#6a5038', borderColor: exp.active ? '#72a848' : '#3e2810' }}
        >
          {exp.active ? 'active' : 'inactive'}
        </span>
        <span className={styles.cardPath}>{exp.folder_path}</span>
      </div>

      <div className={styles.cardActions}>
        {mutationError && !confirming && (
          <span className={styles.cardError}>{mutationError}</span>
        )}
        {exp.active ? (
          confirming ? (
            <>
              <span className={styles.confirmLabel}>Deactivate?</span>
              <Button variant="danger" onClick={handleConfirmDeactivate} disabled={deactivate.isPending}>
                Confirm
              </Button>
              <Button variant="ghost" onClick={() => setConfirming(false)} disabled={deactivate.isPending}>
                Cancel
              </Button>
            </>
          ) : (
            <Button variant="ghost" onClick={() => setConfirming(true)}>
              Deactivate
            </Button>
          )
        ) : (
          <Button
            variant="ghost"
            onClick={() => activate.mutate(exp.folder_path)}
            disabled={activate.isPending}
          >
            Activate
          </Button>
        )}
      </div>
    </div>
  )
}

function CreateModal({ onClose }: { onClose: () => void }) {
  const [folderPath, setFolderPath] = useState('')
  const create = useCreateExperience()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!folderPath.trim()) return
    create.mutate(folderPath.trim(), { onSuccess: onClose })
  }

  return (
    <Modal
      title="New Experience"
      onClose={onClose}
      actions={[
        { label: 'Cancel', variant: 'ghost', onClick: onClose },
        {
          label: create.isPending ? 'Creating…' : 'Create',
          variant: 'primary',
          onClick: () => {
            const form = document.getElementById('create-exp-form') as HTMLFormElement | null
            form?.requestSubmit()
          },
        },
      ]}
    >
      <form id="create-exp-form" onSubmit={handleSubmit} className={styles.form}>
        <label className={styles.label} htmlFor="folder-path">
          Vault folder path
        </label>
        <input
          id="folder-path"
          className={styles.input}
          type="text"
          value={folderPath}
          onChange={e => setFolderPath(e.target.value)}
          placeholder="e.g. electric_racing"
          autoComplete="off"
        />
        <p className={styles.hint}>
          Relative to <code>vault/Experiences/</code> — the folder must already exist.
        </p>
        {create.isError && (
          <p className={styles.formError}>{(create.error as Error).message}</p>
        )}
      </form>
    </Modal>
  )
}

export default function Experiences() {
  const [showCreate, setShowCreate] = useState(false)
  const { data: experiences = [], isLoading, isError } = useExperiences()

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Experiences</h1>
        <Button variant="primary" onClick={() => setShowCreate(true)}>
          New Experience
        </Button>
      </div>

      {isError && (
        <p className={styles.loadError}>Failed to load experiences.</p>
      )}

      {isLoading ? (
        <p className={styles.empty}>Loading…</p>
      ) : experiences.length === 0 ? (
        <p className={styles.empty}>No experiences yet.</p>
      ) : (
        <div className={styles.list}>
          {[...experiences]
            .sort((a, b) => Number(b.active) - Number(a.active))
            .map(exp => (
              <ExperienceCard key={exp.id} exp={exp} />
            ))}
        </div>
      )}

      {showCreate && <CreateModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
