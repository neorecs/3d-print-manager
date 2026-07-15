"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type AuthUser = {
  id: number;
  email: string;
  display_name?: string | null;
  role: "admin" | "operator" | "viewer";
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at?: string | null;
};

type AuditLog = {
  id: number;
  user_id?: number | null;
  action: string;
  summary?: string | null;
  ip_address?: string | null;
  created_at?: string | null;
};

type NewUserForm = {
  email: string;
  display_name: string;
  role: AuthUser["role"];
  password: string;
};

const emptyNewUser: NewUserForm = {
  email: "",
  display_name: "",
  role: "operator",
  password: "",
};

async function readJson(response: Response) {
  const data = await response.json().catch(() => ({ detail: "Geen JSON antwoord." }));
  if (!response.ok) {
    throw new Error(data.detail || `API-fout ${response.status}`);
  }
  return data;
}

function formatDate(value?: string | null) {
  if (!value) return "Nooit";
  return new Intl.DateTimeFormat("nl-NL", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function UserManagement() {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [newUser, setNewUser] = useState<NewUserForm>(emptyNewUser);
  const [passwordResets, setPasswordResets] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeAdminCount = useMemo(() => users.filter((user) => user.role === "admin" && user.is_active).length, [users]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [usersData, auditData] = await Promise.all([
        fetch("/api/auth/users", { cache: "no-store" }).then(readJson),
        fetch("/api/auth/audit-logs?limit=25", { cache: "no-store" }).then(readJson),
      ]);
      setUsers(usersData);
      setAuditLogs(auditData);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Gebruikers konden niet worden geladen.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await fetch("/api/auth/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: newUser.email,
          display_name: newUser.display_name || null,
          role: newUser.role,
          password: newUser.password,
          is_active: true,
        }),
      }).then(readJson);
      setNewUser(emptyNewUser);
      setMessage("Gebruiker aangemaakt.");
      await refresh();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Gebruiker aanmaken mislukt.");
    } finally {
      setSaving(false);
    }
  }

  async function updateUser(user: AuthUser, patch: Partial<AuthUser>) {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await fetch(`/api/auth/users/${user.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: patch.display_name ?? user.display_name ?? "",
          role: patch.role ?? user.role,
          is_active: patch.is_active ?? user.is_active,
        }),
      }).then(readJson);
      setMessage("Gebruiker bijgewerkt.");
      await refresh();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Wijziging mislukt.");
    } finally {
      setSaving(false);
    }
  }

  async function resetPassword(user: AuthUser) {
    const password = passwordResets[user.id] || "";
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await fetch(`/api/auth/users/${user.id}/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      }).then(readJson);
      setPasswordResets((current) => ({ ...current, [user.id]: "" }));
      setMessage(`Wachtwoord reset voor ${user.email}.`);
      await refresh();
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Wachtwoord reset mislukt.");
    } finally {
      setSaving(false);
    }
  }

  async function resetMfa(user: AuthUser) {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await fetch(`/api/auth/users/${user.id}/mfa/reset`, { method: "POST" }).then(readJson);
      setMessage(`MFA reset voor ${user.email}.`);
      await refresh();
    } catch (mfaError) {
      setError(mfaError instanceof Error ? mfaError.message : "MFA reset mislukt.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <form className="grid gap-3 rounded-xl border border-line bg-slate-950/35 p-4 lg:grid-cols-[1.2fr_1fr_.7fr_1fr_auto]" onSubmit={createUser}>
        <input
          className="rounded-lg border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
          onChange={(event) => setNewUser((current) => ({ ...current, email: event.target.value }))}
          placeholder="email@bedrijf.nl"
          required
          type="email"
          value={newUser.email}
        />
        <input
          className="rounded-lg border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
          onChange={(event) => setNewUser((current) => ({ ...current, display_name: event.target.value }))}
          placeholder="Naam"
          value={newUser.display_name}
        />
        <select
          className="rounded-lg border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
          onChange={(event) => setNewUser((current) => ({ ...current, role: event.target.value as AuthUser["role"] }))}
          value={newUser.role}
        >
          <option value="operator">Operator</option>
          <option value="viewer">Viewer</option>
          <option value="admin">Admin</option>
        </select>
        <input
          className="rounded-lg border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
          minLength={12}
          onChange={(event) => setNewUser((current) => ({ ...current, password: event.target.value }))}
          placeholder="Tijdelijk wachtwoord"
          required
          type="password"
          value={newUser.password}
        />
        <button className="rounded-lg bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-50" disabled={saving} type="submit">
          Aanmaken
        </button>
      </form>

      {message ? <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm font-bold text-emerald-200">{message}</div> : null}
      {error ? <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm font-bold text-red-200">{error}</div> : null}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-line text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[.14em] text-muted">
              <th className="px-3 py-3">Gebruiker</th>
              <th className="px-3 py-3">Rol</th>
              <th className="px-3 py-3">Status</th>
              <th className="px-3 py-3">MFA</th>
              <th className="px-3 py-3">Laatste login</th>
              <th className="px-3 py-3">Acties</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {loading ? (
              <tr>
                <td className="px-3 py-4 text-muted" colSpan={6}>Gebruikers laden...</td>
              </tr>
            ) : users.map((user) => {
              const isLastActiveAdmin = user.role === "admin" && user.is_active && activeAdminCount === 1;
              return (
                <tr key={user.id} className="align-top">
                  <td className="px-3 py-4">
                    <input
                      className="mb-2 w-full min-w-48 rounded-lg border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
                      onBlur={(event) => updateUser(user, { display_name: event.target.value })}
                      placeholder="Naam"
                      defaultValue={user.display_name || ""}
                    />
                    <div className="font-black text-ink">{user.email}</div>
                  </td>
                  <td className="px-3 py-4">
                    <select
                      className="rounded-lg border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand disabled:opacity-60"
                      disabled={isLastActiveAdmin || saving}
                      onChange={(event) => updateUser(user, { role: event.target.value as AuthUser["role"] })}
                      value={user.role}
                    >
                      <option value="admin">Admin</option>
                      <option value="operator">Operator</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  </td>
                  <td className="px-3 py-4">
                    <button
                      className={`rounded-lg px-3 py-2 text-xs font-black ${user.is_active ? "bg-emerald-500/15 text-emerald-200" : "bg-slate-800 text-slate-300"} disabled:opacity-60`}
                      disabled={isLastActiveAdmin || saving}
                      onClick={() => updateUser(user, { is_active: !user.is_active })}
                      type="button"
                    >
                      {user.is_active ? "Actief" : "Geblokkeerd"}
                    </button>
                  </td>
                  <td className="px-3 py-4">
                    <div className="mb-2 text-xs font-black text-muted">{user.mfa_enabled ? "Ingeschakeld" : "Uit"}</div>
                    <button
                      className="rounded-lg border border-line px-3 py-2 text-xs font-black text-slate-200 disabled:opacity-50"
                      disabled={!user.mfa_enabled || saving}
                      onClick={() => resetMfa(user)}
                      type="button"
                    >
                      Reset MFA
                    </button>
                  </td>
                  <td className="px-3 py-4 text-muted">{formatDate(user.last_login_at)}</td>
                  <td className="px-3 py-4">
                    <div className="flex min-w-56 flex-col gap-2">
                      <input
                        className="rounded-lg border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
                        minLength={12}
                        onChange={(event) => setPasswordResets((current) => ({ ...current, [user.id]: event.target.value }))}
                        placeholder="Nieuw wachtwoord"
                        type="password"
                        value={passwordResets[user.id] || ""}
                      />
                      <button
                        className="rounded-lg border border-brand/30 bg-brand/10 px-3 py-2 text-xs font-black text-brand disabled:opacity-50"
                        disabled={saving || (passwordResets[user.id] || "").length < 12}
                        onClick={() => resetPassword(user)}
                        type="button"
                      >
                        Reset wachtwoord
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="rounded-xl border border-line bg-slate-950/35">
        <div className="border-b border-line px-4 py-3">
          <h3 className="text-sm font-black text-ink">Recente auditlog</h3>
        </div>
        <div className="divide-y divide-line">
          {auditLogs.length ? auditLogs.map((log) => (
            <div className="grid gap-2 px-4 py-3 text-sm md:grid-cols-[170px_180px_1fr_120px]" key={log.id}>
              <div className="text-muted">{formatDate(log.created_at)}</div>
              <div className="font-black text-slate-200">{log.action}</div>
              <div className="text-slate-300">{log.summary || "-"}</div>
              <div className="text-muted">{log.ip_address || "-"}</div>
            </div>
          )) : <div className="px-4 py-4 text-sm text-muted">Nog geen auditregels.</div>}
        </div>
      </div>
    </div>
  );
}
