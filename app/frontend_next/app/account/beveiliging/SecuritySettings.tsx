"use client";

import QRCode from "qrcode";
import { FormEvent, useEffect, useState } from "react";

type MfaSetup = {
  secret: string;
  otpauth_url: string;
};

type AccountStatus = {
  email: string;
  display_name?: string | null;
  role: "admin" | "operator" | "viewer";
  is_active: boolean;
  must_change_password: boolean;
  mfa_enabled: boolean;
  last_login_at?: string | null;
  session_expires_at?: string | null;
};

function formatDateTime(value?: string | null) {
  if (!value) return "Nog niet bekend";
  return new Intl.DateTimeFormat("nl-NL", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusPill(active: boolean, activeText: string, inactiveText: string) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-black ${active ? "bg-emerald-400/15 text-emerald-200" : "bg-amber-400/15 text-amber-100"}`}>
      {active ? activeText : inactiveText}
    </span>
  );
}

export function SecuritySettings() {
  const [account, setAccount] = useState<AccountStatus | null>(null);
  const [accountError, setAccountError] = useState("");
  const [isLoadingAccount, setIsLoadingAccount] = useState(true);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [setup, setSetup] = useState<MfaSetup | null>(null);
  const [qrCodeUrl, setQrCodeUrl] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);

  useEffect(() => {
    let active = true;
    if (!setup?.otpauth_url) {
      setQrCodeUrl("");
      return;
    }

    QRCode.toDataURL(setup.otpauth_url, {
      errorCorrectionLevel: "M",
      margin: 2,
      scale: 8,
      color: {
        dark: "#020617",
        light: "#ffffff",
      },
    })
      .then((url) => {
        if (active) setQrCodeUrl(url);
      })
      .catch(() => {
        if (active) setQrCodeUrl("");
      });

    return () => {
      active = false;
    };
  }, [setup]);

  async function loadAccountStatus() {
    setAccountError("");
    setIsLoadingAccount(true);
    const response = await fetch("/api/auth/me", { cache: "no-store" });
    const data = await response.json().catch(() => ({ detail: "Accountstatus ophalen mislukt." }));
    setIsLoadingAccount(false);

    if (!response.ok) {
      setAccount(null);
      setAccountError(data.detail || "Accountstatus ophalen mislukt.");
      return;
    }

    setAccount(data);
  }

  useEffect(() => {
    loadAccountStatus();
  }, []);

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
    setMessage("Scan de QR-code met je authenticator-app en vul daarna de 6-cijferige code in.");
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
    await loadAccountStatus();
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
      <section className="xl:col-span-2 rounded-2xl border border-line bg-panel/95 p-5 shadow-card">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-lg font-black text-white">Jouw accountstatus</h2>
            <p className="mt-2 text-sm font-semibold text-muted">
              Controleer hier snel of je account klaar is voor veilig gebruik.
            </p>
          </div>
          <button
            className="w-fit rounded-xl border border-line px-4 py-2 text-sm font-black text-slate-200 transition hover:border-brand hover:text-brand disabled:opacity-50"
            disabled={isLoadingAccount}
            onClick={loadAccountStatus}
            type="button"
          >
            Vernieuwen
          </button>
        </div>

        {accountError ? (
          <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm font-bold text-red-100">{accountError}</div>
        ) : null}

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-line bg-panelSoft p-4">
            <div className="text-xs font-black uppercase tracking-[.14em] text-muted">Ingelogd als</div>
            <div className="mt-2 break-words text-base font-black text-white">{isLoadingAccount ? "Laden..." : account?.display_name || account?.email || "-"}</div>
            <div className="mt-1 break-all text-sm font-semibold text-muted">{account?.email || ""}</div>
          </div>
          <div className="rounded-xl border border-line bg-panelSoft p-4">
            <div className="text-xs font-black uppercase tracking-[.14em] text-muted">Rol en toegang</div>
            <div className="mt-2 text-base font-black capitalize text-white">{account?.role || "-"}</div>
            <div className="mt-3">{statusPill(Boolean(account?.is_active), "Actief", "Geblokkeerd")}</div>
          </div>
          <div className="rounded-xl border border-line bg-panelSoft p-4">
            <div className="text-xs font-black uppercase tracking-[.14em] text-muted">Beveiliging</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {statusPill(Boolean(account && !account.must_change_password), "Wachtwoord klaar", "Wachtwoord wijzigen")}
              {statusPill(Boolean(account?.mfa_enabled), "MFA actief", "MFA uit")}
            </div>
          </div>
          <div className="rounded-xl border border-line bg-panelSoft p-4">
            <div className="text-xs font-black uppercase tracking-[.14em] text-muted">Sessies</div>
            <div className="mt-2 text-sm font-bold text-white">Laatste login</div>
            <div className="text-sm text-muted">{formatDateTime(account?.last_login_at)}</div>
            <div className="mt-2 text-sm font-bold text-white">Deze sessie verloopt</div>
            <div className="text-sm text-muted">{formatDateTime(account?.session_expires_at)}</div>
          </div>
        </div>
      </section>

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
            <div className="rounded-xl border border-line bg-white p-4">
              {qrCodeUrl ? (
                <img
                  alt="MFA QR-code voor authenticator-app"
                  className="mx-auto h-56 w-56"
                  height={224}
                  src={qrCodeUrl}
                  width={224}
                />
              ) : (
                <div className="flex h-56 items-center justify-center rounded-lg bg-slate-100 text-center text-sm font-bold text-slate-700">
                  QR-code wordt gemaakt...
                </div>
              )}
            </div>
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
