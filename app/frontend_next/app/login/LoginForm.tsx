"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function LoginForm({ nextPath }: { nextPath: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [setupSecret, setSetupSecret] = useState("");
  const [setupEmail, setSetupEmail] = useState("");
  const [setupName, setSetupName] = useState("Beheerder");
  const [setupPassword, setSetupPassword] = useState("");
  const [setupMessage, setSetupMessage] = useState("");
  const [setupError, setSetupError] = useState("");
  const [isCreatingAccount, setIsCreatingAccount] = useState(false);
  const [bootstrapAvailable, setBootstrapAvailable] = useState(false);

  useEffect(() => {
    fetch("/api/auth/bootstrap-status")
      .then((response) => response.json())
      .then((data) => setBootstrapAvailable(Boolean(data.available)))
      .catch(() => setBootstrapAvailable(false));
  }, []);

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

  async function handleSetupSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSetupError("");
    setSetupMessage("");
    setIsCreatingAccount(true);

    const response = await fetch("/api/auth/bootstrap-admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bootstrapSecret: setupSecret,
        email: setupEmail,
        displayName: setupName,
        password: setupPassword,
      }),
    });
    const data = await response.json().catch(() => ({ detail: "Account aanmaken mislukt." }));

    if (!response.ok) {
      setSetupError(data.detail || "Account aanmaken mislukt.");
      setIsCreatingAccount(false);
      return;
    }

    setEmail(setupEmail);
    setPassword("");
    setSetupPassword("");
    setSetupSecret("");
    setSetupMessage("Adminaccount aangemaakt. Log nu in met het tijdelijke wachtwoord; daarna moet je direct een eigen wachtwoord kiezen.");
    setIsCreatingAccount(false);
  }

  return (
    <div className="mt-8 space-y-6">
    <form className="space-y-5" onSubmit={handleSubmit}>
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
      {bootstrapAvailable ? <div className="border-t border-line pt-5">
        <button
          className="text-sm font-bold text-brand hover:text-teal-200"
          onClick={() => setShowSetup((value) => !value)}
          type="button"
        >
          Eerste adminaccount aanmaken
        </button>
        {showSetup ? (
          <form className="mt-4 space-y-4 rounded-xl border border-line bg-slate-950/35 p-4" onSubmit={handleSetupSubmit}>
            <p className="text-sm font-semibold text-muted">
              Alleen gebruiken bij eerste installatie. Je hebt de tijdelijke bootstrap-secret nodig.
            </p>
            <div>
              <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="setupSecret">
                Bootstrap-secret
              </label>
              <input
                autoComplete="off"
                className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
                id="setupSecret"
                onChange={(event) => setSetupSecret(event.target.value)}
                required
                type="password"
                value={setupSecret}
              />
            </div>
            <div>
              <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="setupEmail">
                Admin e-mailadres
              </label>
              <input
                autoComplete="email"
                className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
                id="setupEmail"
                onChange={(event) => setSetupEmail(event.target.value)}
                required
                type="email"
                value={setupEmail}
              />
            </div>
            <div>
              <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="setupName">
                Naam
              </label>
              <input
                className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
                id="setupName"
                onChange={(event) => setSetupName(event.target.value)}
                required
                type="text"
                value={setupName}
              />
            </div>
            <div>
              <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="setupPassword">
                Tijdelijk wachtwoord
              </label>
              <input
                autoComplete="new-password"
                className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
                id="setupPassword"
                minLength={12}
                onChange={(event) => setSetupPassword(event.target.value)}
                required
                type="password"
                value={setupPassword}
              />
            </div>
            {setupError ? (
              <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm font-bold text-red-100">
                {setupError}
              </div>
            ) : null}
            {setupMessage ? (
              <div className="rounded-xl border border-teal-300/30 bg-teal-300/10 px-4 py-3 text-sm font-bold text-teal-100">
                {setupMessage}
              </div>
            ) : null}
            <button
              className="w-full rounded-xl border border-line bg-slate-950/60 px-4 py-3 text-sm font-black text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isCreatingAccount}
              type="submit"
            >
              {isCreatingAccount ? "Account aanmaken..." : "Adminaccount aanmaken"}
            </button>
          </form>
        ) : null}
      </div> : null}
    </div>
  );
}
