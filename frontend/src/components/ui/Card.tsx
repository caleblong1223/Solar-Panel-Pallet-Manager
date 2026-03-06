import type { ReactNode } from "react";

type Props = {
  title?: string;
  children: ReactNode;
  className?: string;
};

export default function Card({ title, children, className }: Props) {
  return (
    <article className={["ui-card", className ?? ""].filter(Boolean).join(" ")}>
      {title ? <h2 className="ui-card__title">{title}</h2> : null}
      {children}
    </article>
  );
}
