import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { AUTH_COOKIE_NAME, getSessionFromCookieStore } from "@/lib/auth";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { UserManagement } from "./UserManagement";

export default async function UsersSettingsPage() {
  const cookieStore = await cookies();
  const session = await getSessionFromCookieStore(cookieStore.get(AUTH_COOKIE_NAME)?.value);
  if (session?.role !== "admin") {
    redirect("/");
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Gebruikersbeheer"
        description="Beheer accounts, rollen, toegang en MFA voor de Printfarm Manager."
      />
      <SectionCard title="Accounts" description="Maak gebruikers aan en beheer toegang zonder de laatste actieve admin te verliezen.">
        <UserManagement />
      </SectionCard>
    </div>
  );
}
