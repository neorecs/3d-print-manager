# Backup en herstel

Doel: PostgreSQL backups automatisch maken en herstel aantoonbaar testen voordat echte platformdata wordt gebruikt.

## Automatische backups

De NAS-compose bevat twee backupservices:

- `postgres_backup` voor de database;
- `uploads_backup` voor productfoto's, administratiedocumenten en gekoppelde Bambu Studio-productbestanden.

Beide services hebben een eigen klein Docker-image met het backupscript ingebouwd. Daardoor zijn ze niet afhankelijk van een hostpad naar de broncode en blijven ze ook na een Dockhand-herstart betrouwbaar starten.

Gedrag:

- maakt een backup bij containerstart;
- maakt daarna standaard elke 24 uur een backup;
- gebruikt `pg_dump --format=custom`;
- schrijft een `.sha256` controlebestand;
- bewaart standaard 14 dagen;
- gebruikt dezelfde `DATABASE_URL` als de backend;
- wijzigt niets aan de database.

Standaard bewaarlocatie:

```text
postgres_backups Docker volume
```

De bestandsbackup wordt daaronder opgeslagen in `uploads/` als een `.tar.gz` met eigen `.sha256` controlebestand.
Na een geslaagde run schrijven beide services een marker in `status/`. De live-readiness controleert dat de database- en uploadsmarker niet ouder zijn dan 48 uur.

Wil je een zichtbare NAS-map gebruiken, zet dan in Dockhand:

```env
BACKUP_TARGET_PATH=/backups/3d-print-manager
BACKUP_RETENTION_DAYS=14
BACKUP_INTERVAL_SECONDS=86400
```

## Eenmalige backup testen

Lokaal of op de NAS kan de backupservice eenmalig worden uitgevoerd met:

```bash
BACKUP_RUN_ONCE=true docker compose -f docker-compose.next-nas.yml run --rm postgres_backup
```

## Backupbestand controleren

In de backupmap:

```bash
sha256sum -c print_manager_YYYYMMDDTHHMMSSZ.dump.sha256
```

## Hersteltest

Voer dit uit naar een lege testdatabase, nooit direct over productie heen.

De repository bevat een volledig geisoleerde herstelproef. Deze maakt tijdelijke Docker-volumes, migreert en vult een bron-database, maakt zowel een database- als uploadsbackup, controleert beide checksums en herstelt alles naar een tweede lege database en testmap:

```powershell
python scripts/run_recovery_test.py
```

De tijdelijke containers en volumes worden ook na een mislukking opgeruimd. Dezelfde opdracht draait bij iedere push in GitHub Actions. De proef gebruikt uitsluitend herkenbare testwaarden en benadert geen NAS- of productiedata.

Globale stappen:

1. Maak of kies een lege testdatabase.
2. Kopieer het `.dump` bestand naar een omgeving met `pg_restore`.
3. Restore:

```bash
pg_restore --clean --if-exists --dbname="postgresql://USER:PASSWORD@HOST:5432/TEST_DB" print_manager_YYYYMMDDTHHMMSSZ.dump
```

4. Controleer minimaal:

- producten;
- varianten;
- mediarecords;
- productvoorraad;
- filament;
- orders;
- printjobs;
- accounting;
- Bambu-printers.
5. Pak de bijbehorende uploadsbackup uit in een lege testmap.
6. Controleer minimaal een productfoto, administratiedocument en productprintbestand.

## Backup buiten de NAS

De lokale backups beschermen tegen fouten in de app, maar niet tegen een defecte, gestolen of door ransomware versleutelde NAS: dan zijn data en backups samen weg. Daarom kopieert de service `offsite_backup` de map met lokale backups dagelijks naar opslag buiten de NAS, met [restic](https://restic.net).

- restic versleutelt alles met `RESTIC_PASSWORD` voordat het de NAS verlaat. De opslagaanbieder kan niets lezen.
- Na elke run controleert restic een steekproef (standaard 5%) van de opgeslagen data.
- Bewaarbeleid: 14 dagelijkse, 8 wekelijkse en 12 maandelijkse versies (instelbaar).
- Na een geslaagde run schrijft de service `status/offsite-last-success`. Instellingen toont "Backup buiten de NAS" als die marker niet ouder is dan 48 uur.
- Zonder `RESTIC_REPOSITORY` en `RESTIC_PASSWORD` doet de service niets.

### Instellen in Dockhand

Kies opslag buiten je huis, bijvoorbeeld Backblaze B2, een S3-bucket of een SFTP-server bij iemand anders. Voorbeeld voor Backblaze B2:

```env
OFFSITE_BACKUP_ENABLED=true
RESTIC_REPOSITORY=b2:jouw-bucketnaam:3d-print-manager
RESTIC_PASSWORD=<lange willekeurige waarde>
OFFSITE_B2_ACCOUNT_ID=<keyID>
OFFSITE_B2_ACCOUNT_KEY=<applicationKey>
```

Voor S3-compatibele opslag: `RESTIC_REPOSITORY=s3:https://endpoint/bucket/pad` met `OFFSITE_AWS_ACCESS_KEY_ID` en `OFFSITE_AWS_SECRET_ACCESS_KEY`.

**Bewaar `RESTIC_PASSWORD` ook buiten de NAS**, bijvoorbeeld in je wachtwoordmanager. Zonder dat wachtwoord is de offsite backup onbruikbaar.

### Terugzetten vanaf de offsite backup

```sh
docker compose -f docker-compose.next-nas.yml run --rm offsite_backup restic snapshots
docker compose -f docker-compose.next-nas.yml run --rm -v /tmp/herstel:/herstel offsite_backup restic restore latest --target /herstel
```

Daarna staan de database-dump en het uploads-archief in `/tmp/herstel/backups/`. Zet ze terug zoals beschreven onder "Hersteltest".

## Go/no-go

Zonder geslaagde hersteltest:

- geen echte Etsy/Shopify live import;
- geen echte platformpublicatie;
- geen brede echte AI-modus met productiedata.

Zonder recente backup buiten de NAS: geen echte platformtokens opslaan.

## Laatste hersteltest

Datum: 2026-09-12

- Verse PostgreSQL 16-installatie via alle Alembic-migraties: geautomatiseerd
- Databasebackup en checksum: geautomatiseerd
- Uploadsbackup en checksum: geautomatiseerd
- Restore naar afzonderlijke lege PostgreSQL-database: geautomatiseerd
- Hersteld productrecord en exacte inhoud van uploadbestand: geautomatiseerd
- Tijdelijke containers en volumes verwijderen: geautomatiseerd

Dit bewijst de technische herstelketen. Voor livegang blijft daarnaast periodiek een proef met een echte productiebackup nodig; leg daarvan datum en uitkomst vast zonder persoonsgegevens of secrets in Git te zetten.
