"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function LoginForm({ nextPath }: { nextPath: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, mfaCode }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: "Inloggen mislukt." }));
      if (data.mfa_required) {
        setMfaRequired(true);
        setError(data.detail || "Vul je MFA-code in.");
      } else {
        setMfaRequired(false);
        setMfaCode("");
        setError(data.detail || "Inloggen mislukt.");
      }
      setIsSubmitting(false);
      return;
    }

    router.replace(nextPath || "/");
    router.refresh();
  }

  return (
    <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
      <div>
        <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="email">
          E-mailadres
        </label>
        <input
          autoComplete="email"
          autoFocus
          className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
          id="email"
          name="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          type="email"
          value={email}
        />
      </div>
      <div>
        <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="password">
          Wachtwoord
        </label>
        <input
          autoComplete="current-password"
          className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
          id="password"
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </div>
      {mfaRequired ? (
        <div>
          <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="mfaCode">
            MFA-code
          </label>
          <input
            autoComplete="one-time-code"
            className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
            id="mfaCode"
            inputMode="numeric"
            maxLength={6}
            name="mfaCode"
            onChange={(event) => setMfaCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
            pattern="[0-9]{6}"
            placeholder="123456"
            required
            type="text"
            value={mfaCode}
          />
        </div>
      ) : null}
      {error ? (
        <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm font-bold text-red-100">
          {error}
        </div>
      ) : null}
      <button
        className="w-full rounded-xl bg-brand px-4 py-3 text-sm font-black text-slate-950 shadow-card transition hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? "Bezig met inloggen..." : "Inloggen"}
      </button>
    </form>
  );
}
