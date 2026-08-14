# Backup en herstel

Doel: PostgreSQL backups automatisch maken en herstel aantoonbaar testen voordat echte platformdata wordt gebruikt.

## Automatische backups

De NAS-compose bevat twee backupservices:

- `postgres_backup` voor de database;
- `uploads_backup` voor productfoto's, administratiedocumenten en `.gcode.3mf` printbestanden.

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

## Go/no-go

Zonder geslaagde hersteltest:

- geen echte Etsy/Shopify live import;
- geen echte platformpublicatie;
- geen brede echte AI-modus met productiedata.

## Laatste hersteltest

Datum: 2026-08-14

- Databasebackup: `print_manager_20260814T122224Z.dump`
- Databasechecksum: OK
- Restore naar tijdelijke database: OK, inclusief controle van de producttabel
- Uploadsbackup: `print_manager_uploads_20260814T122224Z.tar.gz`
- Uploadschecksum en archiefinhoud: OK
- Tijdelijke database verwijderd: OK
