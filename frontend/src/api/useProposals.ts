import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { TaskProposal, ApproveProposalRequest } from "../types";

const API = "/api";

export function useProposals(status?: string) {
  const params = status ? `?status=${status}` : "";
  return useQuery<TaskProposal[]>({
    queryKey: ["proposals", status],
    queryFn: async () => {
      const res = await fetch(`${API}/proposals${params}`);
      if (!res.ok) throw new Error("Failed to fetch proposals");
      return res.json();
    },
  });
}

export function useApproveProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, overrides }: { id: number; overrides?: ApproveProposalRequest }) => {
      const res = await fetch(`${API}/proposals/${id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(overrides ?? {}),
      });
      if (!res.ok) throw new Error("Failed to approve proposal");
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["proposals"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useRejectProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`${API}/proposals/${id}/reject`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to reject proposal");
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["proposals"] }),
  });
}

export function useBatchRejectRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ingestionRunId: number) => {
      const res = await fetch(`${API}/proposals/batch-reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ingestion_run_id: ingestionRunId }),
      });
      if (!res.ok) throw new Error("Failed to batch reject");
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["proposals"] }),
  });
}

export function useApproveAllPending() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API}/proposals/approve-all`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to approve all");
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["proposals"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function usePendingProposalCount() {
  const { data } = useProposals("pending");
  return data?.length ?? 0;
}
