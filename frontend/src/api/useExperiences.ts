// src/api/useExperiences.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Experience } from "../types";

async function fetchExperiences(activeOnly?: boolean): Promise<Experience[]> {
  // Only pass ?active=true when explicitly filtering; omitting returns all
  const qs = activeOnly === true ? "?active=true" : "";
  const res = await fetch(`/api/experiences${qs}`);
  if (!res.ok) throw new Error(`Failed to fetch experiences: ${res.status}`);
  return res.json();
}

export function useExperiences(activeOnly?: boolean) {
  return useQuery({
    queryKey: ["experiences", activeOnly],
    queryFn: () => fetchExperiences(activeOnly),
  });
}

export function useCreateExperience() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (folder_path: string): Promise<Experience> => {
      const res = await fetch("/api/experiences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_path }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw Object.assign(new Error(data.detail ?? `Error ${res.status}`), {
          status: res.status,
        });
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiences"] });
    },
  });
}

export function useDeactivateExperience() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const res = await fetch(`/api/experiences/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw Object.assign(new Error(data.detail ?? `Error ${res.status}`), {
          status: res.status,
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiences"] });
    },
  });
}
