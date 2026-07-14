# Projectplan auth en wereldwijde toegang

## Doel

De 3D Print Manager krijgt een productiewaardige loginbasis, zodat de app later veilig buiten het lokale netwerk gebruikt kan worden.

Dit projectplan hoort bij de stap van intern NAS-dashboard naar beveiligde cockpit:

- Next.js beschermt de gebruikersinterface en Next.js API-routes.
- FastAPI krijgt databasegebruikers, loginvalidatie en auditlogs.
- MFA/TOTP wordt voorbereid en daarna gefaseerd verplicht gemaakt.
- De backend en database blijven niet publiek bereikbaar.

## Huidige status

Eerste basis aanwezig:

- Next.js loginpagina op `/login`.
- Login/logout/session routes onder `/api/auth/*`.
- Ondertekende HTTP-only sessiecookie.
- Login rate limiting op de Next.js loginroute.
- Routebescherming via Next.js proxy.
- Logoutknop in de AppShell.
- Optionele env-admin login voor eerste lokale werking.
- Optionele backend-login via `AUTH_BACKEND_LOGIN=true`.
- Backend `users` tabel voorbereid.
- Backend `audit_logs` tabel voorbereid.
- Backend `/auth/login`.
- Backend `/auth/bootstrap-admin` voor de eerste admin.
- Password hashing via PBKDF2-SHA256.
- TOTP helperfuncties, databasevelden en setup/confirm-endpoints voorbereid.

Nog niet klaar:

- MFA/TOTP is nog niet verplicht in de loginflow.
- Er is nog geen gebruikersbeheerpagina.
- Rollen zijn datamodelmatig voorbereid via `role`, maar nog niet per scherm/actie afgedwongen.
- Backend API-routebescherming is nog niet volledig per endpoint afgedwongen; de belangrijkste bescherming is nu dat FastAPI intern moet blijven.

## Environment

Frontend / Next.js:

```env
AUTH_ENABLED=true
AUTH_SECRET=
AUTH_ADMIN_EMAIL=
AUTH_ADMIN_NAME=Beheerder
AUTH_ADMIN_PASSWORD=
AUTH_BACKEND_LOGIN=true
```

Backend / FastAPI:

```env
AUTH_BOOTSTRAP_SECRET=
```

Gebruik `AUTH_BOOTSTRAP_SECRET` alleen tijdelijk voor het aanmaken van de eerste admin. Daarna leegmaken of verwijderen.

## Fase 1 - Loginfundament

Status: grotendeels klaar.

Taken:

1. Loginpagina maken.
2. Sessiecookies ondertekenen.
3. Routes beschermen.
4. Logout toevoegen.
5. Configuratie documenteren.
6. Next.js build groen houden.

Acceptatie:

- Niet-ingelogde gebruikers worden naar `/login` gestuurd.
- API-routes geven `401` zonder sessie.
- Inloggen zet een HTTP-only cookie.
- Uitloggen wist de cookie.

## Fase 2 - Databasegebruikers

Status: basis aanwezig.

Taken:

1. `users` tabel.
2. Password hashing.
3. `/auth/bootstrap-admin`.
4. `/auth/login`.
5. Next.js kan tegen backend-login praten met `AUTH_BACKEND_LOGIN=true`.
6. Auditlog voor admin bootstrap en loginpogingen.

Acceptatie:

- Eerste admin kan eenmalig via bootstrap worden aangemaakt.
- Login faalt voor fout wachtwoord.
- Login slaagt voor bestaand actief account.
- Loginpogingen worden gelogd.

## Fase 3 - MFA/TOTP

Status: voorbereid, nog niet geactiveerd.

Taken:

1. TOTP secret genereren. Status: basis klaar via `/auth/mfa/setup`.
2. Secret versleuteld opslaan. Status: basis klaar via `CREDENTIAL_ENCRYPTION_KEY`.
3. QR-code of handmatige setup-key tonen. Status: otpauth-url en secret worden door de backend teruggegeven; frontendscherm volgt nog.
4. Verificatiecode controleren. Status: basis klaar via `/auth/mfa/confirm`.
5. MFA verplicht maken voor adminaccounts. Status: open.
6. Recoveryproces documenteren. Status: open.

Acceptatie:

- Admin kan MFA aanzetten.
- Login vraagt om code als `mfa_enabled=true`.
- Foute code blokkeert login.
- MFA-secret wordt niet plaintext teruggegeven via API.

## Fase 4 - Rollen en audit

Status: voorbereid, nog niet afgedwongen.

Rollen:

- `admin`: alles beheren.
- `operator`: orders, voorraad, filament, printplanning.
- `viewer`: alleen lezen.

Audit uitbreiden voor:

- voorraadcorrecties;
- platformcredentials;
- publicatie/sync-acties;
- administratiecorrecties;
- gebruikersbeheer;
- MFA wijzigingen.

## Go-live voorwaarden

Geen publieke toegang voordat dit groen is:

- `AUTH_ENABLED=true`.
- `AUTH_BACKEND_LOGIN=true`.
- `AUTH_SECRET` is lang en uniek.
- Eerste admin bestaat in de database.
- `AUTH_BOOTSTRAP_SECRET` is verwijderd of leeg.
- FastAPI is niet publiek bereikbaar.
- PostgreSQL is niet publiek bereikbaar.
- HTTPS actief.
- Backup en restore-test recent gecontroleerd.
- MFA voor admin is actief zodra fase 3 klaar is.

## Lokale testcontainer

Voor de auth/loginbasis is een minimale testcompose aanwezig:

```powershell
docker compose -f docker-compose.test.yml run --rm backend_tests
```

Als Docker Desktop draait maar Codex `permission denied while trying to connect to the docker API at npipe:////./pipe/docker_engine` meldt, heeft de Codex-sandboxgebruiker geen toegang tot de Docker named pipe. Start Docker Desktop handmatig en voer het commando eventueel in een gewone PowerShell uit, of geef de gebruikte Windows-gebruiker toegang tot Docker Desktop.
