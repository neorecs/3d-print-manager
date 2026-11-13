# Secretrotatie

Waarom: het bestand `docs/NAS_COMPOSE_BACKUP_3d-print-manager.yml` stond van 26 juni tot 12 september 2026 in deze repository en staat nog in de git-historie. Het bevatte onder andere het databasewachtwoord, `DATABASE_URL` en `CREDENTIAL_ENCRYPTION_KEY`. Al die waarden moeten als bekend worden beschouwd.

Reken op ongeveer 30 minuten, plus een kort onderhoudsmoment: tussen stap 5 en 6 kunnen printers en verkoopkanalen hun opgeslagen toegangscodes even niet ontsleutelen, en na stap 5 moet iedereen opnieuw inloggen.

## 1. Verse backup

Maak eerst een backup en controleer de checksum, zoals in `BACKUP_EN_HERSTEL.md` onder "Eenmalige backup testen". Noteer de bestandsnaam.

## 2. Nieuwe waarden maken

Op je eigen computer, in de map van de repository:

```sh
python scripts/generate_rotated_secrets.py --db-host <host:poort uit je huidige DATABASE_URL>
```

Het script toont nieuwe waarden en schrijft niets weg. Bewaar ze tijdelijk in je wachtwoordmanager.

## 3. Databasewachtwoord wijzigen

Het wachtwoord staat in PostgreSQL zelf; alleen de environment variable aanpassen is niet genoeg. Open een shell in de databasecontainer (in Dockhand: container `db` → Console, of via ssh):

```sh
docker exec -it <naam-van-db-container> psql -U print_manager -d print_manager
```

```sql
ALTER USER print_manager WITH PASSWORD '<nieuwe POSTGRES_PASSWORD>';
\q
```

Zet daarna in de database-stack ook `POSTGRES_PASSWORD` op de nieuwe waarde. PostgreSQL gebruikt die alleen bij een lege database, maar zo blijven ze gelijk.

## 4. Environment van de app aanpassen in Dockhand

In de stack van `docker-compose.next-nas.yml`:

| Variabele | Nieuwe waarde |
| --- | --- |
| `CREDENTIAL_ENCRYPTION_KEY_OLD` | de **huidige** `CREDENTIAL_ENCRYPTION_KEY` |
| `CREDENTIAL_ENCRYPTION_KEY` | de nieuwe sleutel uit stap 2 |
| `DATABASE_URL` | de nieuwe `DATABASE_URL` uit stap 2 |
| `AUTH_SECRET` | nieuw |
| `BACKEND_INTERNAL_TOKEN` | nieuw |
| `AUTH_BOOTSTRAP_SECRET` | leeg |

Backend en frontend lezen dezelfde waarden, dus je past ze maar op één plek aan.

## 5. Opnieuw uitrollen

Rol de stack opnieuw uit in Dockhand. Iedereen is nu uitgelogd, want de sessies zijn met de oude `AUTH_SECRET` ondertekend.

## 6. Opgeslagen secrets opnieuw versleutelen

Platformtokens, MFA-geheimen en printertoegangscodes staan versleuteld in de database. Zet ze over naar de nieuwe sleutel. In de backendcontainer:

```sh
python tools/reencrypt_credentials.py
```

Dit controleert alleen en toont aantallen. Klopt het, dan:

```sh
python tools/reencrypt_credentials.py --apply
```

De opdracht verandert alles in één transactie, of niets als er iets niet te ontsleutelen is. Hij kan veilig vaker worden uitgevoerd.

## 7. Oude sleutel weghalen

Maak `CREDENTIAL_ENCRYPTION_KEY_OLD` leeg en rol nog een keer uit.

## 8. Controleren

- Inloggen werkt, MFA werkt.
- **Instellingen** toont geen blokkades voor databaseverbinding, interne authenticatie of versleuteling.
- **Printers**: "Verbinding testen" werkt voor elke printer.
- **Verkoopkanalen**: opgeslagen credentials staan op "versleuteld".
- `python tools/reencrypt_credentials.py` meldt alles als "al met de nieuwe sleutel".

## 9. De git-historie

Rotatie maakt de oude waarden waardeloos. De historie opschonen hoeft daarna niet meer voor de veiligheid. Kies daarna zelf:

- **Repository privé maken** in GitHub (Settings → General → Danger Zone). Eenvoudig en zonder gevolgen voor de code.
- **Historie opschonen** met `git filter-repo --path docs/NAS_COMPOSE_BACKUP_3d-print-manager.yml --invert-paths`. Dit herschrijft alle commits; elke bestaande kloon en openstaande branch moet daarna opnieuw worden opgehaald.

## Terug als het misgaat

- Inloggen of database werkt niet na stap 5: zet `DATABASE_URL` terug, of controleer of het wachtwoord in stap 3 en 4 exact gelijk is.
- Stap 6 meldt waarden die niet te ontsleutelen zijn: er is niets gewijzigd. Controleer of `CREDENTIAL_ENCRYPTION_KEY_OLD` exact de vorige sleutel is.
- Als laatste redmiddel: zet de backup uit stap 1 terug zoals beschreven in `BACKUP_EN_HERSTEL.md`, met de oude waarden.
