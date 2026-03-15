// src/api/useGmailAuth.ts
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

export interface GmailAuthStatus {
  connected: boolean;
}

async function fetchStatus(): Promise<GmailAuthStatus> {
  const res = await fetch("/api/auth/gmail/status");
  if (!res.ok) throw new Error("Failed to fetch Gmail auth status");
  return res.json();
}

async function fetchConnectUrl(): Promise<string> {
  const res = await fetch("/api/auth/gmail/connect");
  if (!res.ok) throw new Error("Failed to get Gmail connect URL");
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data.url;
}

export function useGmailAuth() {
  const queryClient = useQueryClient();
  const [connectError, setConnectError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["gmail-auth-status"],
    queryFn: fetchStatus,
  });

  async function connect() {
    setConnectError(null);
    try {
      const url = await fetchConnectUrl();
      window.location.href = url;
    } catch (err) {
      setConnectError(err instanceof Error ? err.message : "Failed to connect Gmail");
    }
  }

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["gmail-auth-status"] });
  }

  return {
    connected: data?.connected ?? false,
    isLoading,
    connect,
    connectError,
    invalidate,
  };
}
