// src/components/ui/Button.tsx
import styles from "./Button.module.css";

type ButtonVariant = "primary" | "ghost" | "danger";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export default function Button({ variant = "ghost", className, children, ...props }: ButtonProps) {
  return (
    <button
      className={[styles.btn, styles[variant], className].filter(Boolean).join(" ")}
      {...props}
    >
      {children}
    </button>
  );
}
