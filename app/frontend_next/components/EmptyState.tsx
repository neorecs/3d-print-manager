type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-slate-950/25 px-4 py-8 text-center">
      <div className="font-bold text-ink">{title}</div>
      <p className="mt-2 text-sm text-muted">{description}</p>
    </div>
  );
}
