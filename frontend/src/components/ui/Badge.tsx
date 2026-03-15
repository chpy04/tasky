// src/components/ui/Badge.tsx
import styles from "./Badge.module.css";

interface BadgeProps {
  variant: "experience";
  label: string;
}

export default function Badge({ label }: BadgeProps) {
  return <span className={styles.experienceBadge}>{label}</span>;
}
