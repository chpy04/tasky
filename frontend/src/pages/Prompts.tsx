import { useActivePromptConfig, usePrompts } from "../api/usePrompts";
import PromptComposer from "../components/prompts/PromptComposer";
import styles from "./Prompts.module.css";

export default function Prompts() {
  const { data: prompts, isLoading, isError, refetch } = usePrompts();
  const { data: activeConfig } = useActivePromptConfig();

  const systemPrompt = prompts?.find((p) => p.kind === "system");
  const sourcePrompts = prompts?.filter((p) => p.kind === "source_context") ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Prompts</h1>
          <span className={styles.subtitle}>Drag source blocks into the canvas</span>
          {activeConfig && <span className={styles.configBadge}>config: {activeConfig.name}</span>}
        </div>
      </div>

      {isLoading && <p className={styles.statusMessage}>Loading…</p>}

      {isError && (
        <div className={styles.errorState}>
          <p className={styles.errorMessage}>Failed to load prompts.</p>
          <button className={styles.retryBtn} onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {!isLoading && !isError && !systemPrompt && (
        <p className={styles.statusMessage}>No system prompt configured.</p>
      )}

      {systemPrompt && <PromptComposer systemPrompt={systemPrompt} sourcePrompts={sourcePrompts} />}
    </div>
  );
}
