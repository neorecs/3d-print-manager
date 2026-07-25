"use client";

import { FormEvent, useState } from "react";
import { useSearchParams } from "next/navigation";

export function ChangePasswordForm() {
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next") || "/";
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (newPassword.length < 12) {
      setError("Gebruik minimaal 12 tekens voor je nieuwe wachtwoord.");
      return;
    }
    if (newPassword !== repeatPassword) {
      setError("De nieuwe wachtwoorden zijn niet gelijk.");
      return;
    }

    setIsSubmitting(true);
    const response = await fetch("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ currentPassword, newPassword }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: "Wachtwoord wijzigen mislukt." }));
      setError(data.detail || "Wachtwoord wijzigen mislukt.");
      setIsSubmitting(false);
      return;
    }

    window.location.assign(nextPath.startsWith("/") ? nextPath : "/");
  }

  return (
    <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
      <div>
        <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="currentPassword">
          Tijdelijk wachtwoord
        </label>
        <input
          autoComplete="current-password"
          className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
          id="currentPassword"
          onChange={(event) => setCurrentPassword(event.target.value)}
          required
          type="password"
          value={currentPassword}
        />
      </div>
      <div>
        <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="newPassword">
          Nieuw wachtwoord
        </label>
        <input
          autoComplete="new-password"
          className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
          id="newPassword"
          minLength={12}
          onChange={(event) => setNewPassword(event.target.value)}
          required
          type="password"
          value={newPassword}
        />
      </div>
      <div>
        <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="repeatPassword">
          Herhaal nieuw wachtwoord
        </label>
        <input
          autoComplete="new-password"
          className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
          id="repeatPassword"
          minLength={12}
          onChange={(event) => setRepeatPassword(event.target.value)}
          required
          type="password"
          value={repeatPassword}
        />
      </div>
      {error ? <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm font-bold text-red-100">{error}</div> : null}
      <button
        className="w-full rounded-xl bg-brand px-4 py-3 text-sm font-black text-slate-950 shadow-card transition hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? "Wachtwoord opslaan..." : "Nieuw wachtwoord opslaan"}
      </button>
    </form>
  );
}
