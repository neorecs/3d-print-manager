# Backup en herstel

Doel: PostgreSQL backups automatisch maken en herstel aantoonbaar testen voordat echte platformdata wordt gebruikt.

## Automatische backup

De NAS-compose bevat een `postgres_backup` service.

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

## Go/no-go

Zonder geslaagde hersteltest:

- geen echte Etsy/Shopify live import;
- geen echte platformpublicatie;
- geen brede echte AI-modus met productiedata.

## Laatste hersteltest

Datum: 2026-06-29

- Backup: `print_manager_20260629T203756Z.dump`
- Checksum: OK
- Restore naar tijdelijke database: OK
- Tijdelijke database verwijderd: OK
