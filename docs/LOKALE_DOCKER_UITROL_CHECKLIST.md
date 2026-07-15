# Lokale Docker-uitrol checklist

Doel: de volledige 3D Print Manager lokaal draaien met PostgreSQL, FastAPI backend en Next.js frontend, inclusief echte database-login en MFA-flow.

## 1. Werkmap en branch

```powershell
cd C:\Users\neorec\Documents\Codex\2026-07-14\ok\work\3d-print-manager
git checkout main
git pull origin main
```

## 2. Lokale omgeving maken

Maak een `.env` vanuit het voorbeeld als die nog niet bestaat:

```powershell
Copy-Item .env.example .env
```

Zet minimaal deze waarden in `.env`:

```env
POSTGRES_DB=print_manager
POSTGRES_USER=print_manager
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+psycopg://print_manager:change-me@db:5432/print_manager
BACKEND_CORS_ORIGINS=http://localhost:38502,http://localhost:38080
FRONTEND_NEXT_API_BASE_URL=http://backend:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:38080

AUTH_ENABLED=true
AUTH_SECRET=zet-hier-een-lange-willekeurige-lokale-secret
AUTH_BACKEND_LOGIN=true
AUTH_BOOTSTRAP_SECRET=tijdelijke-bootstrap-secret

CONNECTORS_LIVE_MODE=false
CREDENTIAL_ENCRYPTION_KEY=zet-hier-een-echte-fernet-key
```

Genereer later een echte `CREDENTIAL_ENCRYPTION_KEY` via de backend:

```powershell
Invoke-RestMethod http://localhost:38080/credentials/generate-key
```

Vervang daarna de tijdelijke waarde in `.env` en herstart de containers.

## 3. Stack bouwen en starten

```powershell
docker compose up --build -d db backend frontend_next
docker compose ps
```

Open:

- Next.js app: http://localhost:38502
- Backend docs: http://localhost:38080/docs
- Backend health: http://localhost:38080/health

## 4. Eerste admin aanmaken

Voer dit eenmalig uit zolang `AUTH_BOOTSTRAP_SECRET` gevuld is:

```powershell
Invoke-RestMethod -Method Post http://localhost:38080/auth/bootstrap-admin `
  -ContentType "application/json" `
  -Body '{"bootstrap_secret":"tijdelijke-bootstrap-secret","email":"admin@example.com","password":"lang-sterk-wachtwoord-123","display_name":"Beheerder"}'
```

Maak daarna `AUTH_BOOTSTRAP_SECRET` leeg in `.env` en herstart backend en frontend:

```powershell
docker compose up -d --build backend frontend_next
```

## 5. Login en gebruikersbeheer testen

1. Open http://localhost:38502.
2. Log in met de eerste admin.
3. Open `Instellingen` > `Gebruikers`.
4. Maak een tweede gebruiker aan.
5. Test rol wijzigen, blokkeren, wachtwoord reset en MFA reset.
6. Controleer dat de laatste actieve admin niet geblokkeerd of gedegradeerd kan worden.

## 6. MFA testen

Start MFA setup via de backend docs of een API-call:

```powershell
$setup = Invoke-RestMethod -Method Post http://localhost:38080/auth/mfa/setup `
  -ContentType "application/json" `
  -Body '{"email":"admin@example.com","password":"lang-sterk-wachtwoord-123"}'

$setup.otpauth_url
$setup.secret
```

Voeg de secret toe aan een authenticator-app en bevestig MFA:

```powershell
Invoke-RestMethod -Method Post http://localhost:38080/auth/mfa/confirm `
  -ContentType "application/json" `
  -Body '{"email":"admin@example.com","password":"lang-sterk-wachtwoord-123","code":"123456"}'
```

Log daarna uit en opnieuw in. De login moet na email en wachtwoord om een MFA-code vragen.

## 7. Acceptatie voor deze lokale uitrol

- `docker compose ps` toont `db`, `backend` en `frontend_next` als draaiend.
- `/health` geeft een gezonde backend terug.
- Next.js toont zonder sessie het loginscherm.
- Eerste admin kan inloggen.
- Gebruikersbeheer werkt alleen voor admins.
- MFA-enabled gebruiker krijgt pas een sessie na geldige code.
- Auditlogs tonen login, MFA en beheeracties.
- Connectoren blijven in mockmodus: `CONNECTORS_LIVE_MODE=false`.

## 8. Stoppen of opnieuw beginnen

Stoppen zonder database te wissen:

```powershell
docker compose down
```

Volledig opnieuw beginnen met lege database:

```powershell
docker compose down -v
docker compose up --build -d db backend frontend_next
```
