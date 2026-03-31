// src/pages/Ingestion.tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  usePreview,
  useIngestionRuns,
  useIngestionRun,
  useCreateIngestionRun,
  useRerunIngestionRun,
  useDeleteIngestionRun,
  useRunPrompt,
  useRunProposals,
  useProposeTasksForRun,
} from "../api/useIngestion";
import type { SourceId, IngestionRunSummary, RunProposal } from "../api/useIngestion";
import { useGmailAuth } from "../api/useGmailAuth";
import styles from "./Ingestion.module.css";

// ── Icons ─────────────────────────────────────────────────────────────────────

function GitHubIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <path
        d="M7 1C3.69 1 1 3.69 1 7c0 2.65 1.72 4.9 4.1 5.69.3.06.41-.13.41-.29v-1.02c-1.67.36-2.02-.8-2.02-.8-.27-.7-.67-.88-.67-.88-.55-.37.04-.36.04-.36.6.04.92.62.92.62.54.92 1.41.65 1.75.5.06-.39.21-.65.38-.8-1.33-.15-2.73-.67-2.73-2.97 0-.66.24-1.19.62-1.61-.06-.15-.27-.76.06-1.59 0 0 .5-.16 1.65.62A5.76 5.76 0 0 1 7 4.68c.51 0 1.02.07 1.5.2 1.14-.78 1.64-.62 1.64-.62.33.83.12 1.44.06 1.59.39.42.62.95.62 1.61 0 2.31-1.41 2.82-2.75 2.97.22.19.41.56.41 1.13v1.67c0 .16.11.35.41.29C11.28 11.9 13 9.65 13 7c0-3.31-2.69-6-6-6Z"
        fill="currentColor"
      />
    </svg>
  );
}

function GmailIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <path
        d="M1 3.5A1.5 1.5 0 0 1 2.5 2h9A1.5 1.5 0 0 1 13 3.5v7A1.5 1.5 0 0 1 11.5 12h-9A1.5 1.5 0 0 1 1 10.5v-7Z"
        stroke="currentColor"
        strokeWidth="1"
        fill="none"
      />
      <path
        d="M1.5 3.5 7 7.5l5.5-4"
        stroke="currentColor"
        strokeWidth="1"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SlackIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <rect x="5" y="1" width="2" height="5" rx="1" fill="currentColor" />
      <rect x="7" y="5" width="5" height="2" rx="1" fill="currentColor" />
      <rect x="7" y="8" width="2" height="5" rx="1" fill="currentColor" />
      <rect x="2" y="7" width="5" height="2" rx="1" fill="currentColor" />
    </svg>
  );
}

function CanvasIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1" fill="none" />
      <path d="M4.5 7h5M7 4.5v5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
    </svg>
  );
}

// ── Source config ──────────────────────────────────────────────────────────────

interface SourceConfig {
  id: SourceId;
  name: string;
  desc: string;
  icon: React.ReactNode;
  emptyText: string;
}

const SOURCES: SourceConfig[] = [
  {
    id: "github",
    name: "GitHub",
    desc: "notifications · last 7 days",
    icon: <GitHubIcon />,
    emptyText: "no notifications in the last 7 days",
  },
  {
    id: "gmail",
    name: "Gmail",
    desc: "actionable emails · last 7 days",
    icon: <GmailIcon />,
    emptyText: "no emails in the last 7 days",
  },
  {
    id: "slack",
    name: "Slack",
    desc: "channel messages · last 7 days",
    icon: <SlackIcon />,
    emptyText: "no messages in the last 7 days",
  },
  {
    id: "canvas",
    name: "Canvas",
    desc: "assignments & announcements · last 7 days",
    icon: <CanvasIcon />,
    emptyText: "no updates in the last 7 days",
  },
];

// ── Source card ────────────────────────────────────────────────────────────────

interface SourceCardProps {
  source: SourceConfig;
  authConnected?: boolean;
  onConnect?: () => void;
  connectError?: string | null;
}

function SourceCard({ source, authConnected, onConnect, connectError }: SourceCardProps) {
  const { mutate, data, isPending, error, isSuccess } = usePreview(source.id);
  const needsConnect = authConnected === false;
  const [open, setOpen] = useState(false);

  const batch = data?.batches[0];
  const parsed = batch
    ? (() => {
        try {
          return JSON.parse(batch.payload);
        } catch {
          return batch.payload;
        }
      })()
    : null;

  return (
    <div className={styles.sourceCard}>
      <div className={styles.sourceHeader}>
        <div className={styles.sourceTitle}>
          {source.icon}
          <span className={styles.sourceName}>{source.name}</span>
          <span className={styles.sourceDesc}>{source.desc}</span>
        </div>
        {needsConnect ? (
          <Button variant="primary" onClick={onConnect}>
            connect
          </Button>
        ) : (
          <Button variant="ghost" onClick={() => mutate()} disabled={isPending}>
            {isPending ? "fetching…" : "fetch"}
          </Button>
        )}
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
                  {" · "}
                  {data.api_calls} api calls
                  {" · "}
                  {(data.duration_ms / 1000).toFixed(2)}s{" · "}${data.llm_cost.toFixed(4)}
                  {batch && <> · {batch.payload.length.toLocaleString()} chars</>}
                  {batch && <> · since {new Date(batch.metadata.since).toLocaleDateString()}</>}
                </span>
              )}
            </div>

            {data.item_count === 0 ? (
              <p className={styles.empty}>{source.emptyText}</p>
            ) : (
              batch && (
                <div className={styles.batchBlock}>
                  <button
                    className={styles.payloadToggle}
                    onClick={() => setOpen((o) => !o)}
                    aria-expanded={open}
                  >
                    <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}>▶</span>
                    payload ({data.item_count} {batch.metadata.kind})
                  </button>

                  {open && (
                    <pre className={styles.payloadPre}>{JSON.stringify(parsed, null, 2)}</pre>
                  )}
                </div>
              )
            )}
          </>
        )}

        {needsConnect && (
          <>
            {connectError && (
              <div className={styles.statusStrip}>
                <span className={styles.statusError}>✗ {connectError}</span>
              </div>
            )}
            <p className={styles.empty}>connect your {source.name} account to enable ingestion</p>
          </>
        )}

        {!needsConnect && !isSuccess && !error && !isPending && (
          <p className={styles.empty}>press fetch to pull data from {source.name}</p>
        )}
      </div>
    </div>
  );
}

// ── Sources section ────────────────────────────────────────────────────────────

function SourcesSection() {
  const gmailAuth = useGmailAuth();
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Sources</h2>
      <div className={styles.previewCards}>
        {SOURCES.map((source) => (
          <SourceCard
            key={source.id}
            source={source}
            authConnected={source.id === "gmail" ? gmailAuth.connected : undefined}
            onConnect={source.id === "gmail" ? gmailAuth.connect : undefined}
            connectError={source.id === "gmail" ? gmailAuth.connectError : undefined}
          />
        ))}
      </div>
    </div>
  );
}

// ── New run form ─────────────────────────────────────────────────────────────

function NewRunForm() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const createRun = useCreateIngestionRun();

  const handleSubmit = () => {
    if (!startDate) return;
    createRun.mutate({ start_date: startDate, ...(endDate ? { end_date: endDate } : {}) });
  };

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>New Ingestion Run</h2>
      <div className={styles.runForm}>
        <label className={styles.dateLabel}>
          start
          <input
            type="datetime-local"
            className={styles.dateInput}
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </label>
        <label className={styles.dateLabel}>
          end <span className={styles.sourceDesc}>(optional — defaults to now)</span>
          <input
            type="datetime-local"
            className={styles.dateInput}
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </label>
        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={!startDate || createRun.isPending}
        >
          {createRun.isPending ? "running…" : "run ingestion"}
        </Button>
      </div>
      {createRun.error && (
        <div className={styles.statusStrip}>
          <span className={styles.statusError}>✗ {(createRun.error as Error).message}</span>
        </div>
      )}
    </div>
  );
}

// ── Batch card ───────────────────────────────────────────────────────────────

function BatchCard({ batch }: { batch: import("../api/useIngestion").IngestionBatchDetail }) {
  const [open, setOpen] = useState(false);

  let parsed: unknown = null;
  try {
    parsed = JSON.parse(batch.raw_payload);
  } catch {
    parsed = batch.raw_payload;
  }

  const successClass =
    batch.success === true
      ? styles.statusOk
      : batch.success === false
        ? styles.statusError
        : styles.statusMeta;

  return (
    <div className={styles.batchBlock}>
      <button
        className={styles.payloadToggle}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}>▶</span>
        <span>{batch.source_type}</span>
        <span className={styles.pipe}>|</span>
        <span className={successClass}>{batch.status}</span>
        {batch.item_count !== null && (
          <>
            <span className={styles.pipe}>|</span>
            <span>{batch.item_count} items</span>
          </>
        )}
        {batch.api_calls !== null && (
          <>
            <span className={styles.pipe}>|</span>
            <span>{batch.api_calls} api calls</span>
          </>
        )}
        {batch.duration_ms !== null && (
          <>
            <span className={styles.pipe}>|</span>
            <span>{(batch.duration_ms / 1000).toFixed(2)}s</span>
          </>
        )}
        {batch.llm_cost !== null && (
          <>
            <span className={styles.pipe}>|</span>
            <span>${batch.llm_cost.toFixed(4)}</span>
          </>
        )}
        <span className={styles.pipe}>|</span>
        <span>{batch.payload_chars.toLocaleString()} chars</span>
      </button>
      {open && <pre className={styles.payloadPre}>{JSON.stringify(parsed, null, 2)}</pre>}
    </div>
  );
}

// ── Run prompt tab ────────────────────────────────────────────────────────────

function RunPromptTab({ runId }: { runId: number }) {
  const prompt = useRunPrompt(runId);
  const [copied, setCopied] = useState(false);

  const combined = prompt.data
    ? prompt.data.system_prompt + "\n\n---\n\n" + prompt.data.user_prompt
    : null;

  const handleCopy = () => {
    if (!combined) return;
    navigator.clipboard.writeText(combined).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  if (prompt.isLoading) return <p className={styles.empty}>loading prompt…</p>;
  if (prompt.error) {
    return (
      <div className={styles.statusStrip}>
        <span className={styles.statusError}>✗ {(prompt.error as Error).message}</span>
      </div>
    );
  }
  if (!combined) return null;

  return (
    <div className={styles.promptSection}>
      <div className={styles.promptHeader}>
        <span className={styles.statusMeta}>
          {combined.length.toLocaleString()} chars · {prompt.data!.token_count.toLocaleString()}{" "}
          tokens
        </span>
        <button className={styles.copyBtn} onClick={handleCopy}>
          {copied ? "copied" : "copy"}
        </button>
      </div>
      <div className={styles.promptMarkdown}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{combined}</ReactMarkdown>
      </div>
    </div>
  );
}

// ── Proposal card ─────────────────────────────────────────────────────────────

function ProposalCard({ proposal }: { proposal: RunProposal }) {
  const [open, setOpen] = useState(false);

  const statusClass =
    proposal.status === "approved"
      ? styles.statusOk
      : proposal.status === "rejected"
        ? styles.statusError
        : styles.statusMeta;

  return (
    <div className={styles.batchBlock}>
      <button
        className={styles.payloadToggle}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}>▶</span>
        <span>{proposal.proposal_type}</span>
        <span className={styles.pipe}>|</span>
        <span className={statusClass}>{proposal.status}</span>
        {proposal.proposed_title && (
          <>
            <span className={styles.pipe}>|</span>
            <span>{proposal.proposed_title}</span>
          </>
        )}
        {proposal.reason_summary && (
          <>
            <span className={styles.pipe}>|</span>
            <span className={styles.sourceDesc}>{proposal.reason_summary}</span>
          </>
        )}
      </button>
      {open && <pre className={styles.payloadPre}>{JSON.stringify(proposal, null, 2)}</pre>}
    </div>
  );
}

// ── Run proposals tab ─────────────────────────────────────────────────────────

function RunProposalsTab({
  runId,
  proposeError,
  isPending,
}: {
  runId: number;
  proposeError: Error | null;
  isPending: boolean;
}) {
  // Poll proposals at 2.5 s while a propose job is in flight.
  const proposals = useRunProposals(runId, isPending);

  return (
    <>
      {isPending && (
        <div className={styles.statusStrip}>
          <span className={styles.statusMeta}>generating proposals…</span>
        </div>
      )}
      {proposeError && (
        <div className={styles.statusStrip}>
          <span className={styles.statusError}>✗ {proposeError.message}</span>
        </div>
      )}
      {proposals.isLoading && <p className={styles.empty}>loading proposals…</p>}
      {proposals.data && proposals.data.length === 0 && !isPending && (
        <p className={styles.empty}>no proposals yet — click propose tasks to generate</p>
      )}
      {proposals.data?.map((p) => (
        <ProposalCard key={p.id} proposal={p} />
      ))}
    </>
  );
}

// ── Run row ──────────────────────────────────────────────────────────────────

type InnerTab = "sources" | "prompt" | "proposals";
type DisplayStatus = "running" | "ingested" | "completed" | "failed";

function fmtDateNoYear(dateStr: string): string {
  const d = new Date(dateStr);
  const date = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const time = d
    .toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true })
    .toLowerCase()
    .replace(" ", "");
  return `${date}, ${time}`;
}

function getDisplayStatus(
  run: IngestionRunSummary,
  isProposing: boolean,
  proposeSuccess: boolean,
): DisplayStatus {
  if (isProposing || run.status === "running") return "running";
  if (run.status === "failed") return "failed";
  if (run.status === "completed") {
    if (proposeSuccess || run.proposal_count > 0) return "completed";
    return "ingested";
  }
  return "ingested";
}

function RunRow({ run }: { run: IngestionRunSummary }) {
  const [expanded, setExpanded] = useState(false);
  const [innerTab, setInnerTab] = useState<InnerTab>("sources");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const isPlaceholder = run.id === -1;
  const detail = useIngestionRun(expanded && !isPlaceholder ? run.id : null);
  const rerun = useRerunIngestionRun();
  const deleteRun = useDeleteIngestionRun();
  const { mutation: proposeTasks, isProposing } = useProposeTasksForRun();

  const displayStatus = getDisplayStatus(run, isProposing, proposeTasks.isSuccess);
  const proposalCount = run.proposal_count > 0 ? run.proposal_count : null;

  const statusCls = {
    running: styles.runStatusRunning,
    ingested: styles.runStatusIngested,
    completed: styles.runStatusCompleted,
    failed: styles.runStatusFailed,
  }[displayStatus];

  return (
    <div className={styles.sourceCard}>
      <div className={styles.runCardHeader}>
        <button
          className={styles.runCardToggle}
          onClick={() => !isPlaceholder && setExpanded((o) => !o)}
          aria-expanded={expanded}
          disabled={isPlaceholder}
        >
          <span className={`${styles.chevron} ${expanded ? styles.chevronOpen : ""}`}>▶</span>
          <span className={`${styles.runStatusBadge} ${statusCls}`}>{displayStatus}</span>
          <span className={styles.runTriggerLabel}>{run.triggered_by}</span>
          <span className={styles.runDateRange}>
            {run.range_start ? fmtDateNoYear(run.range_start) : "?"}
            {" → "}
            {run.range_end ? fmtDateNoYear(run.range_end) : "now"}
          </span>
          {proposalCount !== null && (
            <span className={styles.runMetaChips}>
              <span className={styles.runMetaChip}>
                {proposalCount} {proposalCount === 1 ? "proposal" : "proposals"}
              </span>
            </span>
          )}
        </button>
        {!isPlaceholder && (
          <div className={styles.runActions}>
            <Button variant="ghost" onClick={() => rerun.mutate(run.id)} disabled={rerun.isPending}>
              {rerun.isPending ? "re-running…" : "re-run"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => proposeTasks.mutate(run.id)}
              disabled={proposeTasks.isPending || isProposing}
            >
              {isProposing ? "proposing…" : "propose tasks"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => setConfirmDelete(true)}
              disabled={deleteRun.isPending}
            >
              {deleteRun.isPending ? "deleting…" : "delete"}
            </Button>
          </div>
        )}
      </div>

      {expanded && !isPlaceholder && (
        <>
          <div className={styles.innerTabs}>
            {(["sources", "prompt", "proposals"] as InnerTab[]).map((t) => (
              <button
                key={t}
                className={`${styles.innerTab} ${innerTab === t ? styles.innerTabActive : ""}`}
                onClick={() => setInnerTab(t)}
              >
                {t}
              </button>
            ))}
          </div>
          <div className={styles.sourceBody}>
            {innerTab === "sources" && (
              <>
                <div className={styles.sourcesStats}>
                  <span className={styles.statusMeta}>
                    {run.batch_count} {run.batch_count === 1 ? "batch" : "batches"}
                  </span>
                  <span className={styles.pipe}>·</span>
                  <span className={styles.statusMeta}>
                    {run.total_chars.toLocaleString()} chars
                  </span>
                  {run.finished_at && (
                    <>
                      <span className={styles.pipe}>·</span>
                      <span className={styles.statusMeta}>
                        {(
                          (new Date(run.finished_at).getTime() -
                            new Date(run.started_at).getTime()) /
                          1000
                        ).toFixed(1)}
                        s
                      </span>
                    </>
                  )}
                </div>
                {run.error_summary && (
                  <div className={styles.statusStrip}>
                    <span className={styles.statusError}>{run.error_summary}</span>
                  </div>
                )}
                {detail.isLoading && <p className={styles.empty}>loading batches…</p>}
                {detail.data?.batches.map((batch) => (
                  <BatchCard key={batch.id} batch={batch} />
                ))}
              </>
            )}
            {innerTab === "prompt" && <RunPromptTab runId={run.id} />}
            {innerTab === "proposals" && (
              <RunProposalsTab
                runId={run.id}
                proposeError={proposeTasks.error as Error | null}
                isPending={isProposing}
              />
            )}
          </div>
        </>
      )}

      {confirmDelete && (
        <Modal
          title="Delete Run"
          onClose={() => setConfirmDelete(false)}
          actions={[
            { label: "cancel", onClick: () => setConfirmDelete(false), variant: "ghost" },
            {
              label: "delete",
              onClick: () => {
                setConfirmDelete(false);
                deleteRun.mutate(run.id);
              },
              variant: "danger",
            },
          ]}
        >
          <p className={styles.empty} style={{ fontStyle: "normal" }}>
            Delete run #{run.id} and all its batches? This cannot be undone.
          </p>
        </Modal>
      )}
    </div>
  );
}

// ── Runs list ────────────────────────────────────────────────────────────────

function RunsList() {
  const { data: runs, isLoading } = useIngestionRuns();

  if (isLoading) return <p className={styles.empty}>loading runs…</p>;

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Ingestion Runs</h2>
      {!runs?.length ? (
        <p className={styles.empty}>no ingestion runs yet</p>
      ) : (
        <div className={styles.body}>
          {runs.map((run) => (
            <RunRow key={run.id} run={run} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

type PageTab = "sources" | "runs";

export default function Ingestion() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState<PageTab>("runs");
  const gmailAuth = useGmailAuth();

  useEffect(() => {
    if (searchParams.get("gmail") === "connected") {
      gmailAuth.invalidate();
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams, gmailAuth]);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Ingestion</h1>
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${tab === "sources" ? styles.tabActive : ""}`}
            onClick={() => setTab("sources")}
          >
            sources
          </button>
          <button
            className={`${styles.tab} ${tab === "runs" ? styles.tabActive : ""}`}
            onClick={() => setTab("runs")}
          >
            runs
          </button>
        </div>
      </div>
      <div className={styles.body}>
        {tab === "sources" && <SourcesSection />}
        {tab === "runs" && (
          <>
            <NewRunForm />
            <RunsList />
          </>
        )}
      </div>
    </div>
  );
}
