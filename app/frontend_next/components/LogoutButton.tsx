"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function LogoutButton() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [authEnabled, setAuthEnabled] = useState(false);

  useEffect(() => {
    fetch("/api/auth/session")
      .then((response) => response.json())
      .then((data) => setAuthEnabled(Boolean(data.authEnabled)))
      .catch(() => setAuthEnabled(false));
  }, []);

  async function handleLogout() {
    setIsSubmitting(true);
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  if (!authEnabled) return null;

  return (
    <button
      className="whitespace-nowrap rounded-full border border-line bg-panelSoft px-2.5 py-1 text-[11px] font-black text-slate-200 transition hover:border-brand/50 hover:text-white disabled:opacity-60 sm:px-3 sm:text-xs"
      disabled={isSubmitting}
      onClick={handleLogout}
      type="button"
    >
      Uitloggen
    </button>
  );
}
