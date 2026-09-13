# V1.0 livegang-runbook

Doel: de 3D Print Manager gecontroleerd live-klaar maken voor echte producten, voorraad, orders en later Etsy/Shopify-koppelingen.

## Beslisregel

Gebruik drie afzonderlijke beslissingen. Een blokkade in een latere fase maakt een eerdere fase niet rood:

1. **Intern live:** echte producten, voorraad, printers en administratie op het vertrouwde lokale netwerk.
2. **Platform live:** echte Etsy- of Shopify-tokens en een gecontroleerde proef per platform.
3. **Extern bereikbaar:** gebruikers openen de website via internet; bewust uitgesteld tot een domein en HTTPS.

De actuele functionele en operationele status staat uitsluitend in `ACCEPTATIECHECKLIST.md`. Dit runbook beschrijft de werkwijze. Het scherm Instellingen levert runtimebewijs met tijdstippen; CI-bewijs vervangt geen productiehersteltest.

## Harde voorwaarden

| Punt | Status | Actie |
| --- | --- | --- |
| Next.js is hoofdfrontend | klaar | Gebruik `http://10.5.1.150:38502/` als hoofdscherm. |
| Backend healthcheck | klaar in compose | NAS-compose controleert `/health`. |
| Frontend healthcheck | klaar in compose | NAS-compose controleert de Next.js startpagina. |
| PostgreSQL database | runtimecontrole | Instellingen moet bevestigen dat de database bereikbaar is. |
| Secrets buiten Git | actie vereist | Een oud NAS-composebackupbestand stond in Git. Roteer alle daarin gebruikte waarden voor livegang; verwijdering uit de huidige branch wist Git-historie niet. |
| Connector mockmodus | klaar | `CONNECTORS_LIVE_MODE=false` houden tot live platformtest. |
| Backup aanwezig | runtimecontrole | Instellingen toont datum en geldigheid van de laatste databasebackup. |
| Bestandsbackup aanwezig | runtimecontrole | Instellingen toont datum en geldigheid van de laatste backup van uploads. |
| Gezamenlijke hersteltest | CI klaar, productie apart controleren | De geisoleerde CI-restore is bewezen; Instellingen moet daarnaast een recente productiehersteltest met datum tonen. |
| Voorraadconcurrency | klaar in code | Rijvergrendeling en databaseconstraints voorkomen normale overreservering. |
| Rollen | klaar in hoofdinterface | Viewer is alleen-lezen; credentials, gebruikers en fiscale instellingen zijn admin-only. |
| AI-kostenlimiet | klaar in code | Daglimiet en tokenregistratie zijn aanwezig; echte AI blijft standaard uit. |
| Etsy live test | open | Pas na backup/herstel en juiste credentials. |
| Shopify live test | open | Pas na backup/herstel en juiste credentials. |
| Administratiecontrole | deels klaar | Basis aanwezig; fiscale instellingen laten controleren. |

HTTPS staat niet in deze tabel als blokkade voor intern gebruik of uitgaande platformcalls. Voor toegang tot de website via internet blijft het wel een harde voorwaarde, samen met een domein, secure cookies en een aparte beveiligingscontrole.

## Livefase 1: intern live

Toegestaan:

- echte producten invoeren;
- echte productfoto's uploaden;
- echte productvarianten, SKU's, printtijd en filamentverbruik vastleggen;
- echte voorraad en filamentrollen beheren;
- Bambu-printers registreren;
- orders handmatig of via mockimport testen;
- printplanning en Bambu-export gebruiken;
- administratiebasis gebruiken als intern hulpmiddel.

Niet doen:

- `CONNECTORS_LIVE_MODE=true` zetten;
- automatisch publiceren naar Etsy/Shopify;
- echte platformorders importeren zonder backup/hersteltest;
- OpenAI echte modus breed aanzetten zonder kostenlimiet.

## Livefase 2: eerste platformtest

Voer dit per platform uit, niet Etsy en Shopify tegelijk.

1. Maak een backup.
2. Controleer herstelprocedure.
3. Voeg credentials toe via verkoopkanaalinstellingen.
4. Laat `CONNECTORS_LIVE_MODE=false`.
5. Controleer connectorstatus en ontbrekende credentials.
6. Zet `CONNECTORS_LIVE_MODE=true` alleen voor een bewuste test.
7. Test eerst lezen/importeren, daarna pas publiceren/syncen.
8. Zet live-modus terug naar false als de test klaar is.
9. Controleer importlogs, publicatiefouten en databasegegevens.

## Backup minimale implementatie

Dagelijks:

```text
pg_dump -> /backups/3d-print-manager/daily/
retentie -> 14 dagen
```

Bewaar ook:

- datum/tijd backup;
- database naam;
- app commit/hash;
- resultaat van laatste restore-test.
- de bijbehorende uploadsbackup met checksum.

## Hersteltest

1. Maak backup van productie-database.
2. Start lege testdatabase.
3. Restore backup.
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
5. Noteer uitkomst in dit document of in een apart log.

### Uitgevoerde productiehersteltest

Datum: 2026-06-29

Backupbestand:

```text
print_manager_20260629T203756Z.dump
```

Resultaat:

- checksum: OK;
- restore naar tijdelijke database: OK;
- tijdelijke database na controle verwijderd: OK.

Gecontroleerde tellingen:

| Tabel | Aantal |
| --- | ---: |
| products | 3 |
| product_variants | 3 |
| product_inventory | 1 |
| orders | 3 |
| filament_spools | 1 |
| print_jobs | 2 |
| accounting_sales | 0 |
| bambu_printers | 1 |

### Geautomatiseerde gezamenlijke hersteltest

Sinds 2026-09-12 voert GitHub Actions een verse PostgreSQL-installatie en een gezamenlijke database- plus uploadsbackup/restore uit. Lokaal is dezelfde geisoleerde proef beschikbaar via `python scripts/run_recovery_test.py`. Deze test gebruikt geen NAS-data en maakt de runtimecontrole voor een productiehersteltest daarom niet automatisch groen.

## Verplichte secretrotatie voor livegang

Een eerder bijgehouden NAS-composebackup bevatte configuratiewaarden en is uit de huidige branch verwijderd en genegeerd. Omdat de repository publiek is geweest, moeten alle waarden uit dat bestand als bekend worden beschouwd. Roteer minimaal het databasewachtwoord, de credential-encryptiesleutel en alle sessie-, interne en bootstrapsecrets. Controleer ook printeraccesscodes en platformtokens als die ooit in dezelfde configuratie stonden. Git-historie opschonen is een afzonderlijke, verstorende actie en vervangt rotatie niet.

## Go/no-go voor Etsy/Shopify

Go alleen als:

- backup is bewezen;
- gezamenlijke database- en bestandenrestore is bewezen;
- `CREDENTIAL_ENCRYPTION_KEY` definitief is;
- connectorstatus toont welke credentials aanwezig zijn;
- testproduct klaarstaat;
- testorderflow bekend is;
- je weet hoe je live-modus terug uitzet.

No-go als:

- backup ontbreekt;
- restore niet getest is;
- credentials nog met tijdelijke key zijn opgeslagen;
- publicatiecontrole fouten toont;
- platformscope onbekend is;
- je niet zeker weet welk product/order getest wordt.

## Aanbevolen volgorde vanaf nu

1. Controleer in Instellingen of intern gebruik geen blokkades en recente bewijsdatums toont.
2. Productcatalogus, voorraad en filament met echte gegevens vullen en praktisch aftekenen.
3. Wacht op Etsy-goedkeuring en voer daarna één gecontroleerde Etsy-proef uit; houd Shopify nog uit.
4. Controleer administratie-uitkomsten met concrete verkoopsituaties.
5. Richt pas bij een eigen domein HTTPS en toegang via internet in.
