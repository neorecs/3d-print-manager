# Lokale Docker-uitrol checklist

Doel: de volledige 3D Print Manager lokaal draaien met PostgreSQL, FastAPI backend en Next.js frontend, inclusief echte database-login en MFA-flow.

## 1. Werkmap en branch

```powershell
cd <pad-naar-de-repository>\3d-print-manager
git checkout main
git pull origin main
```

## 2. Lokale omgeving maken

Genereer een `.env` met unieke lokale secrets en controleer het configuratiecontract:

```powershell
python scripts/initialize_local_env.py
python scripts/validate_configuration.py
```

De initializer zet minimaal deze waarden veilig klaar:

```env
POSTGRES_DB=print_manager
POSTGRES_USER=print_manager
POSTGRES_PASSWORD=<unieke-waarde>
DATABASE_URL=postgresql+psycopg://print_manager:<dezelfde-unieke-waarde>@db:5432/print_manager
BACKEND_CORS_ORIGINS=http://localhost:38502,http://localhost:38080
FRONTEND_NEXT_API_BASE_URL=http://backend:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:38080

AUTH_ENABLED=true
AUTH_SECRET=<unieke-lange-waarde>
BACKEND_INTERNAL_TOKEN=<andere-unieke-lange-waarde>
AUTH_BACKEND_LOGIN=true
AUTH_BOOTSTRAP_SECRET=<tijdelijke-unieke-waarde>

CONNECTORS_LIVE_MODE=false
CREDENTIAL_ENCRYPTION_KEY=<unieke-fernet-key>
```

## 3. Stack bouwen en starten

```powershell
docker compose up --build -d db backend frontend_next
docker compose ps
```

Open:

- Next.js app: http://localhost:38502
- Backend health: http://localhost:38080/health

## 4. Eerste admin aanmaken

Open het Next.js-loginscherm. Zolang `AUTH_BOOTSTRAP_SECRET` gevuld is en er nog geen admin bestaat, verschijnt `Eerste adminaccount aanmaken`. Vul daar de bootstrap-secret uit `.env`, het adminadres en een tijdelijk sterk wachtwoord in.

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

Open na het inloggen `Instellingen` en start daar MFA-configuratie. Scan de QR-code met de authenticator-app en bevestig met de actuele zescijferige code.

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

Gebruik `down -v` alleen voor een bewust lege lokale testinstallatie; nooit voor de NAS-productiestack.

## 9. Gecombineerd herstel testen

Met een draaiende lokale Docker-engine:

```powershell
python scripts/run_recovery_test.py
```

Deze proef gebruikt een afzonderlijke Compose-stack zonder hostpoorten of productievolumes. Database en uploadbestand moeten beide met geldige checksum worden teruggezet en inhoudelijk worden gecontroleerd.
