import Link from "next/link";
type EmptyStateProps = {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
};

export function EmptyState({ title, description, actionHref, actionLabel }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-surfaceSoft px-4 py-8 text-center">
      <div className="font-semibold text-ink">{title}</div>
      <p className="mt-2 text-sm text-muted">{description}</p>
      {actionHref && actionLabel ? (
        <Link className="mt-4 inline-flex rounded-md bg-brand px-4 py-2 text-sm font-semibold text-onBrand" href={actionHref}>
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
