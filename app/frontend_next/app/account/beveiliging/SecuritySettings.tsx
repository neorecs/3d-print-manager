"use client";

import { FormEvent, useState } from "react";

type MfaSetup = {
  secret: string;
  otpauth_url: string;
};

export function SecuritySettings() {
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [setup, setSetup] = useState<MfaSetup | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);

  async function startMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsStarting(true);

    const response = await fetch("/api/auth/mfa/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const data = await response.json().catch(() => ({ detail: "MFA setup starten mislukt." }));
    setIsStarting(false);

    if (!response.ok) {
      setSetup(null);
      setError(data.detail || "MFA setup starten mislukt.");
      return;
    }

    setSetup({ secret: data.secret, otpauth_url: data.otpauth_url });
    setMessage("Voeg de setup-code toe aan je authenticator-app en vul daarna de 6-cijferige code in.");
  }

  async function confirmMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsConfirming(true);

    const response = await fetch("/api/auth/mfa/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password, code }),
    });
    const data = await response.json().catch(() => ({ detail: "MFA bevestigen mislukt." }));
    setIsConfirming(false);

    if (!response.ok) {
      setError(data.detail || "MFA bevestigen mislukt.");
      return;
    }

    setSetup(null);
    setCode("");
    setPassword("");
    setMessage("MFA is ingeschakeld. Bij je volgende login vraagt de app om je 6-cijferige code.");
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
      <section className="rounded-2xl border border-line bg-panel/95 p-5 shadow-card">
        <h2 className="text-lg font-black text-white">MFA instellen</h2>
        <p className="mt-2 text-sm font-semibold text-muted">
          Gebruik dit voor je adminaccount. Je wachtwoord is nodig om MFA bewust te activeren.
        </p>
        <form className="mt-5 space-y-4" onSubmit={startMfa}>
          <div>
            <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="password">
              Huidig wachtwoord
            </label>
            <input
              autoComplete="current-password"
              className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
              id="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </div>
          <button
            className="rounded-xl bg-brand px-4 py-3 text-sm font-black text-slate-950 shadow-card transition hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isStarting}
            type="submit"
          >
            {isStarting ? "Setup starten..." : "MFA setup starten"}
          </button>
        </form>
      </section>

      <section className="rounded-2xl border border-line bg-panel/95 p-5 shadow-card">
        <h2 className="text-lg font-black text-white">Authenticator koppelen</h2>
        {setup ? (
          <div className="mt-5 space-y-4">
            <div className="rounded-xl border border-line bg-slate-950/40 p-4">
              <div className="text-xs font-black uppercase tracking-[.14em] text-muted">Setup-code</div>
              <div className="mt-2 break-all font-mono text-sm font-bold text-white">{setup.secret}</div>
            </div>
            <a className="block break-all text-sm font-bold text-brand hover:text-teal-200" href={setup.otpauth_url}>
              Open in authenticator-app
            </a>
            <form className="space-y-4" onSubmit={confirmMfa}>
              <div>
                <label className="text-xs font-black uppercase tracking-[.14em] text-muted" htmlFor="code">
                  6-cijferige code
                </label>
                <input
                  autoComplete="one-time-code"
                  className="mt-2 w-full rounded-xl border border-line bg-[#111b2d] px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-brand"
                  id="code"
                  inputMode="numeric"
                  maxLength={6}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  pattern="[0-9]{6}"
                  required
                  type="text"
                  value={code}
                />
              </div>
              <button
                className="rounded-xl bg-brand px-4 py-3 text-sm font-black text-slate-950 shadow-card transition hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isConfirming}
                type="submit"
              >
                {isConfirming ? "MFA bevestigen..." : "MFA bevestigen"}
              </button>
            </form>
          </div>
        ) : (
          <div className="mt-5 rounded-xl border border-line bg-panelSoft p-4 text-sm font-semibold text-muted">
            Start eerst de MFA setup. Daarna verschijnt hier de code voor je authenticator-app.
          </div>
        )}
      </section>

      {error ? <div className="xl:col-span-2 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm font-bold text-red-100">{error}</div> : null}
      {message ? <div className="xl:col-span-2 rounded-xl border border-teal-300/30 bg-teal-300/10 px-4 py-3 text-sm font-bold text-teal-100">{message}</div> : null}
    </div>
  );
}
