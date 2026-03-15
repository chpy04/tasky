// src/components/ui/FilterChip.tsx
import styles from "./FilterChip.module.css";

interface FilterChipProps {
  label: string;
  active: boolean;
  onClick: () => void;
  dot?: string; // hex color for the dot indicator
}

export default function FilterChip({ label, active, onClick, dot }: FilterChipProps) {
  return (
    <button className={`${styles.chip} ${active ? styles.active : ""}`} onClick={onClick}>
      {dot && <span className={styles.dot} style={{ background: dot }} />}
      {label}
    </button>
  );
}
