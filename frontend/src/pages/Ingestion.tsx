// src/pages/Ingestion.tsx
import { useState } from 'react'
import Button from '../components/ui/Button'
import { usePreview } from '../api/useIngestion'
import type { SourceId } from '../api/useIngestion'
import styles from './Ingestion.module.css'

// ── Icons ─────────────────────────────────────────────────────────────────────

function GitHubIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <path
        d="M7 1C3.69 1 1 3.69 1 7c0 2.65 1.72 4.9 4.1 5.69.3.06.41-.13.41-.29v-1.02c-1.67.36-2.02-.8-2.02-.8-.27-.7-.67-.88-.67-.88-.55-.37.04-.36.04-.36.6.04.92.62.92.62.54.92 1.41.65 1.75.5.06-.39.21-.65.38-.8-1.33-.15-2.73-.67-2.73-2.97 0-.66.24-1.19.62-1.61-.06-.15-.27-.76.06-1.59 0 0 .5-.16 1.65.62A5.76 5.76 0 0 1 7 4.68c.51 0 1.02.07 1.5.2 1.14-.78 1.64-.62 1.64-.62.33.83.12 1.44.06 1.59.39.42.62.95.62 1.61 0 2.31-1.41 2.82-2.75 2.97.22.19.41.56.41 1.13v1.67c0 .16.11.35.41.29C11.28 11.9 13 9.65 13 7c0-3.31-2.69-6-6-6Z"
        fill="currentColor"
      />
    </svg>
  )
}

function GmailIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <path d="M1 3.5A1.5 1.5 0 0 1 2.5 2h9A1.5 1.5 0 0 1 13 3.5v7A1.5 1.5 0 0 1 11.5 12h-9A1.5 1.5 0 0 1 1 10.5v-7Z" stroke="currentColor" strokeWidth="1" fill="none"/>
      <path d="M1.5 3.5 7 7.5l5.5-4" stroke="currentColor" strokeWidth="1" fill="none" strokeLinecap="round"/>
    </svg>
  )
}

function SlackIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <rect x="5" y="1" width="2" height="5" rx="1" fill="currentColor"/>
      <rect x="7" y="5" width="5" height="2" rx="1" fill="currentColor"/>
      <rect x="7" y="8" width="2" height="5" rx="1" fill="currentColor"/>
      <rect x="2" y="7" width="5" height="2" rx="1" fill="currentColor"/>
    </svg>
  )
}

function CanvasIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1" fill="none"/>
      <path d="M4.5 7h5M7 4.5v5" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
    </svg>
  )
}

// ── Source config ──────────────────────────────────────────────────────────────

interface SourceConfig {
  id: SourceId
  name: string
  desc: string
  icon: React.ReactNode
  emptyText: string
}

const SOURCES: SourceConfig[] = [
  {
    id: 'github',
    name: 'GitHub',
    desc: 'notifications · last 7 days',
    icon: <GitHubIcon />,
    emptyText: 'no notifications in the last 7 days',
  },
  {
    id: 'gmail',
    name: 'Gmail',
    desc: 'actionable emails · last 7 days',
    icon: <GmailIcon />,
    emptyText: 'no emails in the last 7 days',
  },
  {
    id: 'slack',
    name: 'Slack',
    desc: 'channel messages · last 7 days',
    icon: <SlackIcon />,
    emptyText: 'no messages in the last 7 days',
  },
  {
    id: 'canvas',
    name: 'Canvas',
    desc: 'assignments & announcements · last 7 days',
    icon: <CanvasIcon />,
    emptyText: 'no updates in the last 7 days',
  },
]

// ── Source card ────────────────────────────────────────────────────────────────

function SourceCard({ source }: { source: SourceConfig }) {
  const { mutate, data, isPending, error, isSuccess } = usePreview(source.id)
  const [open, setOpen] = useState(false)

  const batch = data?.batches[0]
  const parsed = batch ? (() => {
    try { return JSON.parse(batch.payload) } catch { return batch.payload }
  })() : null

  return (
    <div className={styles.sourceCard}>
      <div className={styles.sourceHeader}>
        <div className={styles.sourceTitle}>
          {source.icon}
          <span className={styles.sourceName}>{source.name}</span>
          <span className={styles.sourceDesc}>{source.desc}</span>
        </div>
        <Button variant="ghost" onClick={() => mutate()} disabled={isPending}>
          {isPending ? 'fetching…' : 'fetch'}
        </Button>
      </div>

      <div className={styles.sourceBody}>
        {error && (
          <div className={styles.statusStrip}>
            <span className={styles.statusError}>✗ {(error as Error).message}</span>
          </div>
        )}

        {isSuccess && data && (
          <>
            <div className={styles.statusStrip}>
              <span className={styles.statusOk}>
                ✓ fetched at {new Date(data.fetched_at).toLocaleTimeString()}
              </span>
              {data.item_count === 0 ? (
                <span className={styles.statusMeta}>{source.emptyText}</span>
              ) : (
                <span className={styles.statusMeta}>
                  {data.item_count} items
                  {' · '}{data.api_calls} api calls
                  {' · '}{(data.duration_ms / 1000).toFixed(2)}s
                  {' · '}${data.llm_cost.toFixed(4)}
                  {batch && <> · {batch.payload.length.toLocaleString()} chars</>}
                  {batch && <> · since {new Date(batch.metadata.since).toLocaleDateString()}</>}
                </span>
              )}
            </div>

            {data.item_count === 0 ? (
              <p className={styles.empty}>{source.emptyText}</p>
            ) : batch && (
              <div className={styles.batchBlock}>
                <button
                  className={styles.payloadToggle}
                  onClick={() => setOpen(o => !o)}
                  aria-expanded={open}
                >
                  <span className={`${styles.chevron} ${open ? styles.chevronOpen : ''}`}>▶</span>
                  payload ({data.item_count} {batch.metadata.kind})
                </button>

                {open && (
                  <pre className={styles.payloadPre}>
                    {JSON.stringify(parsed, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </>
        )}

        {!isSuccess && !error && !isPending && (
          <p className={styles.empty}>press fetch to pull data from {source.name}</p>
        )}
      </div>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Ingestion() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Ingestion</h1>
        <p className={styles.subtitle}>raw data preview — no database writes</p>
      </div>

      <div className={styles.body}>
        {SOURCES.map(source => (
          <SourceCard key={source.id} source={source} />
        ))}
      </div>
    </div>
  )
}
