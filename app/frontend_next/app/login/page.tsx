import { redirect } from "next/navigation";

import { LoginForm } from "./LoginForm";
import { authIsEnabled } from "@/lib/auth";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  const nextPath = params.next && params.next.startsWith("/") ? params.next : "/";

  if (!authIsEnabled()) {
    redirect("/");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-line bg-panel/95 p-6 shadow-card sm:p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand text-sm font-black text-slate-950 shadow-card">
            3D
          </div>
          <div>
            <h1 className="text-xl font-black tracking-normal text-white">3D Print Manager</h1>
            <p className="mt-1 text-sm font-semibold text-muted">Beveiligde toegang tot je printfarm cockpit</p>
          </div>
        </div>
        <LoginForm nextPath={nextPath} />
      </section>
    </main>
  );
}
