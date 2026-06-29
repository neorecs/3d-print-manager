# V1.0 livegang-runbook

Doel: de 3D Print Manager gecontroleerd live-klaar maken voor echte producten, voorraad, orders en later Etsy/Shopify-koppelingen.

## Beslisregel

We gaan pas live met echte platformdata als alle punten in "Harde voorwaarden" groen zijn.

Live betekent hier eerst: intern gebruiken met echte producten, echte voorraad, echte Bambu-printers en eventueel echte administratiegegevens. Etsy/Shopify live-publicatie en orderimport zijn een aparte go/no-go stap.

## Harde voorwaarden

| Punt | Status | Actie |
| --- | --- | --- |
| Next.js is hoofdfrontend | klaar | Gebruik `http://10.5.1.150:38502/` als hoofdscherm. |
| Backend healthcheck | klaar in compose | NAS-compose controleert `/health`. |
| Frontend healthcheck | klaar in compose | NAS-compose controleert de Next.js startpagina. |
| PostgreSQL database | deels klaar | Draait al, maar backup/herstel moet nog bewezen worden. |
| Secrets buiten Git | klaar als werkwijze | Controleer Dockhand env voor `DATABASE_URL` en `CREDENTIAL_ENCRYPTION_KEY`. |
| Connector mockmodus | klaar | `CONNECTORS_LIVE_MODE=false` houden tot live platformtest. |
| Backup aanwezig | open | Dagelijkse PostgreSQL backup op NAS instellen. |
| Hersteltest uitgevoerd | open | Een backup terugzetten naar testdatabase en resultaat noteren. |
| Etsy live test | open | Pas na backup/herstel en juiste credentials. |
| Shopify live test | open | Pas na backup/herstel en juiste credentials. |
| Administratiecontrole | deels klaar | Basis aanwezig; fiscale instellingen laten controleren. |

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

## Go/no-go voor Etsy/Shopify

Go alleen als:

- backup is bewezen;
- restore-test is bewezen;
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

1. NAS healthchecks actief krijgen.
2. PostgreSQL backup automatiseren.
3. Restore-test uitvoeren en noteren.
4. Productcatalogus met echte producten vullen.
5. Voorraad/filament echt invoeren.
6. Shopify als eerste live lezen/importeren testen.
7. Daarna pas Etsy OAuth/publicatie onderzoeken.
