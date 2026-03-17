import type { TaskProposal } from "../../types";
import { ProposalCard } from "./ProposalCard";
import styles from "./ProposalList.module.css";

interface ProposalListProps {
  proposals: TaskProposal[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onRejectRun: (runId: number) => void;
}

interface RunGroup {
  runId: number | null;
  runDate: string | null;
  sourceTags: string[];
  proposals: TaskProposal[];
}

function formatGroupDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

const SOURCE_COLOR: Record<string, string> = {
  slack: "#4a9eff",
  github: "#e8c070",
  gmail: "#8a7058",
  email: "#8a7058",
  canvas: "#4caf50",
};

export function ProposalList({ proposals, selectedId, onSelect, onRejectRun }: ProposalListProps) {
  if (proposals.length === 0) {
    return (
      <div className={styles.empty}>
        <span className={styles.emptyText}>No proposals</span>
      </div>
    );
  }

  // Group proposals by ingestion run id
  const groupMap = new Map<string, RunGroup>();

  for (const p of proposals) {
    const runId = p.ingestion_batch?.ingestion_run?.id ?? null;
    const key = runId !== null ? String(runId) : "manual";

    if (!groupMap.has(key)) {
      const runDate = p.ingestion_batch?.ingestion_run?.started_at ?? p.created_at;
      groupMap.set(key, {
        runId,
        runDate,
        sourceTags: [],
        proposals: [],
      });
    }

    const group = groupMap.get(key)!;
    group.proposals.push(p);

    const src = p.ingestion_batch?.source_type;
    if (src && !group.sourceTags.includes(src)) {
      group.sourceTags.push(src);
    }
  }

  const groups = Array.from(groupMap.values());

  return (
    <div className={styles.list}>
      {groups.map((group) => (
        <div key={group.runId ?? "manual"} className={styles.group}>
          <div className={styles.groupHeader}>
            <div className={styles.groupMeta}>
              <span className={styles.groupDate}>
                {group.runDate ? formatGroupDate(group.runDate) : "Manual"}
              </span>
              <span className={styles.groupCount}>{group.proposals.length}</span>
            </div>
            <div className={styles.groupRight}>
              <div className={styles.sourceTags}>
                {group.sourceTags.map((src) => (
                  <span
                    key={src}
                    className={styles.sourceTag}
                    style={{
                      color: SOURCE_COLOR[src] ?? "#8a7058",
                      borderColor: SOURCE_COLOR[src] ?? "#8a7058",
                    }}
                  >
                    {src}
                  </span>
                ))}
              </div>
              {group.runId !== null && (
                <button
                  className={styles.rejectRunBtn}
                  onClick={() => group.runId !== null && onRejectRun(group.runId)}
                  title="Reject all proposals in this run"
                >
                  reject run
                </button>
              )}
            </div>
          </div>
          <div className={styles.cards}>
            {group.proposals.map((p) => (
              <ProposalCard
                key={p.id}
                proposal={p}
                selected={p.id === selectedId}
                onClick={() => onSelect(p.id)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
