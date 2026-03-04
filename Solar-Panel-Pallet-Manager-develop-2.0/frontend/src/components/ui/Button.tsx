import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "danger";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

export default function Button({ variant = "primary", className = "", children, ...props }: Props) {
  return (
    <button className={`ui-btn ui-btn--${variant} ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}
