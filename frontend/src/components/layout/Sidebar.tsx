// src/components/layout/Sidebar.tsx
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import styles from "./Sidebar.module.css";

function TasksIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="1" y="1" width="5" height="5" stroke="currentColor" strokeWidth="1.2" />
      <rect x="8" y="1" width="5" height="5" stroke="currentColor" strokeWidth="1.2" />
      <rect x="1" y="8" width="5" height="5" stroke="currentColor" strokeWidth="1.2" />
      <rect x="8" y="8" width="5" height="5" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

function ExperiencesIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

function IngestionIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path
        d="M7 1v12M3 5l4-4 4 4M3 9l4 4 4-4"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ProposalsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 2h10v8H2z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
      <path d="M5 5h4M5 7h2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M9 10l1.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M5 10l-1.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

function PromptsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 2h7l3 3v7H2V2z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
      <path d="M9 2v3h3" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
      <path d="M4 6h6M4 8h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.2" />
      <path
        d="M7 1v2M7 11v2M1 7h2M11 7h2M2.93 2.93l1.41 1.41M9.66 9.66l1.41 1.41M2.93 11.07l1.41-1.41M9.66 4.34l1.41-1.41"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function NavIcon({
  to,
  label,
  children,
  end = false,
}: {
  to: string;
  label: string;
  children: ReactNode;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      title={label}
      className={({ isActive }) => `${styles.navIcon} ${isActive ? styles.active : ""}`}
    >
      {children}
    </NavLink>
  );
}

export default function Sidebar() {
  return (
    <nav className={styles.sidebar}>
      <NavIcon to="/" label="Tasks" end>
        <TasksIcon />
      </NavIcon>
      <NavIcon to="/experiences" label="Experiences">
        <ExperiencesIcon />
      </NavIcon>
      <NavIcon to="/ingestion" label="Ingestion">
        <IngestionIcon />
      </NavIcon>
      <NavIcon to="/proposals" label="Proposals">
        <ProposalsIcon />
      </NavIcon>
      <NavIcon to="/prompts" label="Prompts">
        <PromptsIcon />
      </NavIcon>
      <div className={styles.spacer} />
      <NavIcon to="/settings" label="Settings">
        <SettingsIcon />
      </NavIcon>
    </nav>
  );
}
