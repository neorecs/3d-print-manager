import { Suspense } from "react";

import { ChangePasswordForm } from "./ChangePasswordForm";

export default function ChangePasswordPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-line bg-panel/95 p-6 shadow-card sm:p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand text-sm font-black text-slate-950 shadow-card">
            3D
          </div>
          <div>
            <h1 className="text-xl font-black tracking-normal text-white">Wachtwoord wijzigen</h1>
            <p className="mt-1 text-sm font-semibold text-muted">Kies een eigen wachtwoord voordat je verdergaat.</p>
          </div>
        </div>
        <Suspense fallback={null}>
          <ChangePasswordForm />
        </Suspense>
      </section>
    </main>
  );
}
