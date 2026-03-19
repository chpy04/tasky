import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface Prompt {
  id: number;
  key: string;
  kind: string;
  source_type: string | null;
  content: string;
  description: string | null;
  updated_at: string;
}

export interface PromptConfig {
  id: number;
  name: string;
  is_active: boolean;
}

export function usePrompts() {
  return useQuery<Prompt[]>({
    queryKey: ["prompts"],
    queryFn: async () => {
      const res = await fetch("/api/prompts");
      if (!res.ok) throw new Error("Failed to fetch prompts");
      return res.json();
    },
  });
}

export function useActivePromptConfig() {
  return useQuery<PromptConfig>({
    queryKey: ["prompt-configs", "active"],
    queryFn: async () => {
      const res = await fetch("/api/prompt-configs/active");
      if (!res.ok) throw new Error("Failed to fetch active config");
      return res.json();
    },
  });
}

export function useUpdatePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      content,
      description,
    }: {
      id: number;
      content?: string;
      description?: string;
    }): Promise<Prompt> => {
      const res = await fetch(`/api/prompts/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, description }),
      });
      if (!res.ok) throw new Error("Failed to update prompt");
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prompts"] });
    },
  });
}
