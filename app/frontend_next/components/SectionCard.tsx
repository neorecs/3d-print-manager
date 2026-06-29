import { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  description?: string;
  children: ReactNode;
};

export function SectionCard({ title, description, children }: SectionCardProps) {
  return (
    <section className="rounded-2xl border border-line bg-panel/90 shadow-card backdrop-blur">
      <div className="border-b border-line px-4 py-4">
        <h2 className="text-base font-black text-ink">{title}</h2>
        {description ? <p className="mt-1 text-sm text-muted">{description}</p> : null}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}
