"use client";

import { Search } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function GlobalSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    if (value) router.push(`/zoeken?q=${encodeURIComponent(value)}`);
  }

  return (
    <form className="relative hidden w-full max-w-sm md:block" onSubmit={submit} role="search">
      <label className="sr-only" htmlFor="global-search">Zoek in de applicatie</label>
      <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
      <input
        className="w-full rounded-md border border-line bg-slate-950/45 py-2 pl-9 pr-3 text-sm text-ink placeholder:text-muted focus:border-brand"
        id="global-search"
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Zoek product, SKU, order of printer"
        value={query}
      />
    </form>
  );
}
