import { useState } from "react";
import {
  useProposals,
  useApproveProposal,
  useRejectProposal,
  useBatchRejectRun,
  useApproveAllPending,
} from "../api/useProposals";
import type { ApproveProposalRequest } from "../types";
import { ProposalList } from "../components/proposals/ProposalList";
import { ProposalDetail } from "../components/proposals/ProposalDetail";
import Button from "../components/ui/Button";
import styles from "./Proposals.module.css";

type StatusFilter = "pending" | "approved" | "rejected" | "";

const FILTER_TABS: { label: string; value: StatusFilter }[] = [
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
  { label: "All", value: "" },
];

export default function Proposals() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");

  const {
    data: proposals = [],
    isLoading,
    isError,
    refetch,
  } = useProposals(statusFilter || undefined);
  const approveProposal = useApproveProposal();
  const rejectProposal = useRejectProposal();
  const batchRejectRun = useBatchRejectRun();
  const approveAllPending = useApproveAllPending();

  const selectedProposal = proposals.find((p) => p.id === selectedId) ?? null;

  function handleSelect(id: number) {
    setSelectedId(id);
  }

  function handleApprove(id: number, overrides?: ApproveProposalRequest) {
    approveProposal.mutate(
      { id, overrides },
      {
        onSuccess: () => {
          // Auto-advance to the next pending proposal
          const idx = proposals.findIndex((p) => p.id === id);
          const next = proposals.find((p, i) => i > idx && p.status === "pending");
          const prev = [...proposals].reverse().find((p, i) => {
            const origIdx = proposals.length - 1 - i;
            return origIdx < idx && p.status === "pending";
          });
          setSelectedId(next?.id ?? prev?.id ?? null);
        },
      },
    );
  }

  function handleReject(id: number) {
    rejectProposal.mutate(id, {
      onSuccess: () => {
        const idx = proposals.findIndex((p) => p.id === id);
        const next = proposals.find((p, i) => i > idx && p.status === "pending");
        const prev = [...proposals].reverse().find((p, i) => {
          const origIdx = proposals.length - 1 - i;
          return origIdx < idx && p.status === "pending";
        });
        setSelectedId(next?.id ?? prev?.id ?? null);
      },
    });
  }

  function handleRejectRun(runId: number) {
    if (!window.confirm(`Reject all proposals from Run #${runId}?`)) return;
    batchRejectRun.mutate(runId, {
      onSuccess: () => setSelectedId(null),
    });
  }

  function handleApproveAll() {
    const pendingCount = proposals.filter((p) => p.status === "pending").length;
    if (
      !window.confirm(
        `Approve all ${pendingCount} pending proposal${pendingCount !== 1 ? "s" : ""}?`,
      )
    )
      return;
    approveAllPending.mutate(undefined, {
      onSuccess: () => setSelectedId(null),
    });
  }

  function handleRejectAll() {
    const pendingCount = proposals.filter((p) => p.status === "pending").length;
    if (
      !window.confirm(
        `Reject all ${pendingCount} pending proposal${pendingCount !== 1 ? "s" : ""}?`,
      )
    )
      return;
    // Reject each individually
    const pending = proposals.filter((p) => p.status === "pending");
    pending.forEach((p) => rejectProposal.mutate(p.id));
    setSelectedId(null);
  }

  const pendingCount = proposals.filter((p) => p.status === "pending").length;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Proposals</h1>
          <div className={styles.filterTabs}>
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.value}
                className={`${styles.tab} ${statusFilter === tab.value ? styles.tabActive : ""}`}
                onClick={() => {
                  setStatusFilter(tab.value);
                  setSelectedId(null);
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        <div className={styles.headerActions}>
          {statusFilter === "pending" && pendingCount > 0 && (
            <>
              <Button
                variant="primary"
                onClick={handleApproveAll}
                disabled={approveAllPending.isPending}
              >
                {approveAllPending.isPending ? "Approving…" : `Approve All (${pendingCount})`}
              </Button>
              <Button
                variant="danger"
                onClick={handleRejectAll}
                disabled={rejectProposal.isPending}
              >
                Reject All
              </Button>
            </>
          )}
        </div>
      </div>

      {isError && (
        <div className={styles.errorBanner}>
          Failed to load proposals —{" "}
          <button className={styles.retryBtn} onClick={() => refetch()}>
            retry
          </button>
        </div>
      )}

      <div className={`${styles.body} ${isLoading ? styles.loading : ""}`}>
        <div className={styles.listPanel}>
          <ProposalList
            proposals={proposals}
            selectedId={selectedId}
            onSelect={handleSelect}
            onRejectRun={handleRejectRun}
          />
        </div>
        <div className={styles.detailPanel}>
          {selectedProposal ? (
            <ProposalDetail
              proposal={selectedProposal}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ) : (
            <div className={styles.emptyDetail}>
              <span className={styles.emptyDetailText}>Select a proposal to review</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
