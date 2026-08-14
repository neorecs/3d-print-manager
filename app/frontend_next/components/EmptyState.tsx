type EmptyStateProps = {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
};

export function EmptyState({ title, description, actionHref, actionLabel }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-slate-950/25 px-4 py-8 text-center">
      <div className="font-bold text-ink">{title}</div>
      <p className="mt-2 text-sm text-muted">{description}</p>
      {actionHref && actionLabel ? (
        <a className="mt-4 inline-flex rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950" href={actionHref}>
          {actionLabel}
        </a>
      ) : null}
    </div>
  );
}
