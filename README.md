# 3D Print Manager

Centrale beheerlaag voor 3D-printactiviteiten: producten, platformpublicaties, orders, productvoorraad, filament, printplanning, trends, voorraadadvies en exports richting Bambu Studio.

## Status

Versie 0.14 beveiliging, gegevensintegriteit en UX-hardening:

- FastAPI backend
- PostgreSQL database
- SQLAlchemy modellen
- Alembic migration
- FastAPI routes opgesplitst per domein onder `app/backend/api/routes/`
- Businesslogica ondergebracht in services en domeinmodules
- Centrale statuswaarden onder `app/backend/domain/statuses.py`
- Streamlit dashboard/prototype als fallback
- Next.js frontend onder `app/frontend_next`
- Docker Compose
- Dummydata voor testen zonder Etsy- of Shopify-koppelingen
- Producten aanmaken en bewerken via Streamlit
- Productvarianten aanmaken en bewerken via Streamlit
- Filamentrollen aanmaken en bewerken via Streamlit
- Productfoto's/media beheren via Streamlit
- Productfoto's uploaden naar lokale backend-opslag
- Per platformpublicatie kiezen welke productfoto's gebruikt worden en in welke volgorde
- Producttags beheren via Streamlit
- SEO-velden en verkooptekst beheren via Streamlit
- Variantdetails zoals maat, afwerking, gewicht en afmetingen beheren
- Platformen beheren via Streamlit
- Productpublicaties per platform aanmaken en bewerken
- Platformtitel, omschrijving, categorie, tags, prijs en verzendprofiel beheren
- Publicatiecontrole uitvoeren voor verplichte product- en platformvelden
- Publicaties markeren als gepubliceerd, gesynchroniseerd of gepauzeerd
- Orders aanmaken en bewerken via Streamlit
- Orderregels aanmaken via Streamlit
- Orderregels automatisch koppelen aan interne producten/varianten via SKU
- Dummy Etsy- en Shopify-import maken nu nieuwe testorders aan
- Orderdetailpagina toont orderregels met koppelstatus
- Productvoorraad aanmaken en bewerken via Streamlit
- Vrije voorraad tonen als `op voorraad - gereserveerd`
- Voorraadbewegingen tonen
- Orders automatisch controleren tegen vrije voorraad
- Orderregels reserveren voorraad waar beschikbaar
- Alleen het tekort wordt op `quantity_to_print` gezet
- Printtaken automatisch maken voor ordertekorten
- Extra geplande aantallen ondersteunen
- Printresultaten verwerken met gelukt/mislukt/aantal naar order
- Extra gelukte prints toevoegen aan vrije productvoorraad
- Mislukte prints registreren als voorraadbeweging
- Kosteninstellingen beheren
- Filamentkosten berekenen vanuit gramverbruik en filamentprijs
- Verpakking, platformkosten, verzending en stroomkosten meenemen
- Geschatte winst per order berekenen en tonen
- Printbatches aanmaken uit geselecteerde printtaken
- Bambu Studio-pakket per batch downloaden als ZIP met CSV, handleiding en gekoppelde `.gcode.3mf` bestanden
- Een gekoppeld productbestand rechtstreeks downloaden en openen in Bambu Studio
- Productielijst exporteren met ordernummer, aantallen, kleur, materiaal en bestandsnaam
- Orderoverzicht exporteren per batch
- Trendanalyse over 30, 60 en 90 dagen
- Verkoop per productvariant tonen
- Top producten, kleuren en materialen berekenen
- Omzet en geschatte winst per variant/product tonen
- Gemiddelde verkoop per week berekenen
- Voorraadadvies genereren uit gemiddelde weekverkoop
- Veiligheidsvoorraad en vooruitkijkperiode instellen
- Vrije voorraad meenemen in advies
- Advies aanpassen, accepteren of negeren
- Geaccepteerd advies omzetten naar printtaak voor voorraadproductie
- Productwijzigingen zetten gepubliceerde platformpublicaties automatisch op `synchronisatie_nodig`
- Publiceren en synchroniseren leggen `last_synced_at` vast
- Publicatiecontrole bevat aangescherpte Etsy- en Shopify-regels
- Foutmeldingen en sync-status zijn zichtbaar in het Streamlit publicatiescherm
- Connectorlaag voor Etsy/Shopify met veilige mockmodus
- Platformcredentials beheren zonder waarden terug te tonen in API/Streamlit
- Databaseconstraints tegen dubbele imports en ongeldige voorraad
- Transactionele voorraadvergrendeling voor gelijktijdige reserveringen
- Daglimiet en gebruiksregistratie voor betaalde AI-aanvragen
- Begrensde uploads per bestandstype
- Dagelijkse backup van PostgreSQL en de permanente uploadopslag
- Live-readiness op basis van werkelijk recente database-, bestandsbackups en hersteltests
- Backend alleen toegankelijk via de interne frontendverbinding en een geldige, intrekbare gebruikerssessie
- Productmedia, documenten en printbestanden via beveiligde downloadroutes
- Traceerbare handmatige voorraadwijzigingen met gebruiker, bron en voor/na-standen
- Cent-nauwkeurige btw-berekening en blokkade op boeken in afgesloten btw-perioden
- Gepagineerde product- en orderoverzichten en een volledig doorklikbaar dashboard
- Cloudvriendelijke Bambu Studio-workflow als standaard: downloaden, controleren en vanuit Bambu Studio printen
- Directe Bambu-printstart via LAN blijft als ingeklapte geavanceerde optie beschikbaar

Uploads worden lokaal opgeslagen onder `app/backend/uploads/` en alleen na sessiecontrole via `/secure-files/...` geserveerd. Deze map staat in `.gitignore`.

Platformpublicaties kunnen een eigen fotoselectie gebruiken. Als er geen platformselectie is ingesteld, gebruikt de publicatie automatisch de centrale productfoto's op productvolgorde.

## Lokaal starten

1. Kopieer de voorbeeldomgeving:

```powershell
Copy-Item .env.example .env
```

2. Start de containers:

```powershell
docker compose up --build
```

3. Open:

- Next.js dashboard: http://localhost:38502
- Streamlit dashboard/fallback: http://localhost:38501
- FastAPI docs: http://localhost:38080/docs
- Healthcheck: http://localhost:38080/health

De backend voert bij het starten automatisch `alembic upgrade head` uit.

## Frontends

Er zijn tijdelijk twee frontends:

- `app/frontend_streamlit`: bestaande prototype/fallback UI.
- `app/frontend_next`: nieuwe officiële React/Next.js frontend.

De Next.js server gebruikt de FastAPI backend intern via:

```env
API_BASE_URL=http://backend:8000
BACKEND_INTERNAL_TOKEN=een-lange-willekeurige-waarde
```

Streamlit blijft beschikbaar als fallback. Nieuwe productiewaardige schermen en verbeteringen horen in Next.js. De uitfaseringslijst staat in `docs/STREAMLIT_UITFASERING.md`.

## NAS Next.js stack

`docker-compose.next-nas.yml` draait de Next.js frontend samen met een private backendservice. Die backend publiceert geen eigen poort. De browser communiceert uitsluitend met Next.js; Next.js voegt de interne backend-identiteit en gebruikerssessie toe.

Voor NAS-deploy zijn minimaal deze environment variables nodig in Dockhand:

```env
DATABASE_URL=
CREDENTIAL_ENCRYPTION_KEY=
AUTH_SECRET=
BACKEND_INTERNAL_TOKEN=
```

Zet secrets niet in Git. De Next.js service gebruikt intern standaard `http://backend:8000`.

De NAS-compose bevat healthchecks voor:

- backend: `/health`
- frontend_next: Next.js startpagina

Het v1.0 livegang-runbook staat in `docs/V1_LIVEGANG_RUNBOOK.md`. Gebruik dat document als go/no-go lijst voordat echte platformtokens, echte orders of live publicaties worden gebruikt.
Het auth/loginspoor staat in `docs/PROJECTPLAN_AUTH_LOGIN.md`.

De NAS-compose bevat een `postgres_backup` en `uploads_backup` service. Deze bewaren dagelijks zowel PostgreSQL als foto's, documenten en printbestanden. Details staan in `docs/BACKUP_EN_HERSTEL.md`.

## Loginbeveiliging

De Next.js frontend heeft een loginlaag. De NAS-compose zet deze standaard aan; lokaal kun je auth bewust uitzetten met `AUTH_ENABLED=false`.

```env
AUTH_ENABLED=true
AUTH_SECRET=
AUTH_ADMIN_EMAIL=
AUTH_ADMIN_NAME=Beheerder
AUTH_ADMIN_PASSWORD=
AUTH_BACKEND_LOGIN=true
AUTH_COOKIE_SECURE=false
```

Gebruik verschillende lange willekeurige waarden voor `AUTH_SECRET` en `BACKEND_INTERNAL_TOKEN`. De frontend valideert iedere beschermde sessie tegen de database. Wachtwoord-, rol-, MFA- en accountwijzigingen trekken bestaande sessies direct in.

In de NAS-compose valt `AUTH_SECRET` tijdelijk terug op `CREDENTIAL_ENCRYPTION_KEY` als er nog geen losse `AUTH_SECRET` is ingesteld. Voor productie heeft een aparte lange `AUTH_SECRET` de voorkeur.

Gebruik `AUTH_COOKIE_SECURE=false` zolang de app intern via gewone HTTP draait. Zet dit op `true` zodra je HTTPS gebruikt.

Voor databasegebruikers kan de backend een eerste admin aanmaken via `/auth/bootstrap-admin` wanneer `AUTH_BOOTSTRAP_SECRET` tijdelijk is ingesteld. Zet daarna `AUTH_BACKEND_LOGIN=true` op de Next.js service zodat de login tegen de FastAPI `users` tabel controleert. Verwijder of leeg `AUTH_BOOTSTRAP_SECRET` na het aanmaken van de eerste admin.

Voorbeeld bootstrap-call:

```powershell
Invoke-RestMethod -Method Post http://localhost:38080/auth/bootstrap-admin `
  -ContentType "application/json" `
  -Body '{"bootstrap_secret":"tijdelijke-secret","email":"admin@example.com","password":"lang-sterk-wachtwoord","display_name":"Beheerder"}'
```

De backend legt loginpogingen en het aanmaken van de eerste admin vast in `audit_logs`. MFA/TOTP kan backendmatig worden voorbereid via `/auth/mfa/setup` en bevestigd via `/auth/mfa/confirm`. Zodra MFA voor een gebruiker is ingeschakeld, vraagt de loginflow om een geldige TOTP-code voordat de Next.js sessie wordt gezet.

Voor een volledige lokale Docker-uitrol met database-login en MFA staat de checklist in `docs/LOKALE_DOCKER_UITROL_CHECKLIST.md`.

## Platformconnectors

De connectorlaag draait standaard in mockmodus:

```env
CONNECTORS_LIVE_MODE=false
```

In mockmodus krijgen publicaties wel een extern test-ID en een syncdatum, maar er worden geen live Etsy- of Shopify-calls gedaan.

Voor latere live-koppelingen kunnen credentials via environment variables of via het Streamlit-platformscherm worden beheerd:

```env
ETSY_API_KEY=
ETSY_ACCESS_TOKEN=
ETSY_SHOP_ID=
SHOPIFY_ACCESS_TOKEN=
SHOPIFY_SHOP_DOMAIN=
SHOPIFY_API_VERSION=2026-04
```

Credentials die via Streamlit/API worden opgeslagen, worden versleuteld met `CREDENTIAL_ENCRYPTION_KEY`. Genereer voor echte tokens eerst een eigen key:

```powershell
Invoke-RestMethod http://localhost:38080/credentials/generate-key
```

Zet de waarde daarna in `.env` als `CREDENTIAL_ENCRYPTION_KEY`. De Docker Compose fallback-key is alleen bedoeld voor lokaal prototypegebruik.

Shopify live publicatie/synchronisatie gebruikt de Admin GraphQL API `2026-04`. De eerste live scope ondersteunt product aanmaken en productdetails/media synchroniseren. Bulkvarianten, voorraad-sync en echte orderimport volgen nog.

## Tests

De backend heeft dependency-vrije `unittest` tests voor de belangrijkste businessregels. Draai ze in de backend-container:

```powershell
docker compose exec -T backend python -m unittest discover -s tests -v
```

De huidige suite controleert onder andere:

- voorraadreservering en alleen tekort naar printplanning;
- herhaald orderverwerken zonder dubbele reservering;
- blokkeren van negatieve vrije productvoorraad;
- printresultaten verwerken naar order, vrije voorraad en afgekeurde prints;
- publicatievalidatie en mock-publicatie via de connectorlaag;
- Etsy/Shopify connectorfouten zonder live calls in mockmodus;
- voorraadadvies op basis van verkoop, veiligheidsvoorraad en vrije voorraad.
- unieke voorraadregels en databasechecks tegen overreservering;
- Bambu-preflight blokkeert starten zonder gekoppeld remote uploadbestand;
- AI-daglimiet en tokenregistratie.

Voor de volledige backend-suite in een schone testcontainer:

```powershell
docker compose -f docker-compose.test.yml run --rm backend_tests
```

De frontend bouw- en rooktest draait met:

```powershell
Set-Location app/frontend_next
npm install
npm run build
node scripts/smoke-test.mjs
```

De uitgevoerde auditmaatregelen staan in `docs/AUDIT_13_AANBEVELINGEN.md`.

De tests zijn opgesplitst per domein:

```text
app/backend/tests/
  support.py
  test_ai_product_assistant.py
  test_connectors_etsy.py
  test_connectors_shopify.py
  test_inventory.py
  test_planning.py
  test_publishing.py
```

## Acceptatiechecklist

De v1.0-acceptatiecriteria staan in `docs/ACCEPTATIECHECKLIST.md`.

## UI-handleiding

Een praktische klikhandleiding voor het Streamlit-dashboard staat in `docs/UI_HANDLEIDING.md`.

## Dummydata

In het Streamlit-dashboard staat een knop `Dummydata laden`.

Je kunt ook direct de API gebruiken:

```powershell
Invoke-RestMethod -Method Post http://localhost:38080/seed
```

## Architectuur

```text
app/
  backend/
    api/
      routes/
        health.py
        ai.py
        accounting.py
        products.py
        orders.py
        inventory.py
        planning.py
        platforms.py
        bambu.py
        uploads.py
    models/
    schemas/
    domain/
      statuses.py
    services/
      accounting_service.py
      platform_service.py
      product_service.py
      upload_service.py
    connectors/
      etsy/
      shopify/
      woocommerce/
      ebay/
    products/
    inventory/
    planning/
    analytics/
    exports/
    publishing/
  frontend_streamlit/
  frontend_next/
  database/
docs/
docker-compose.yml
.env.example
```

## Belangrijke uitgangspunten

- De backend staat los van de frontend.
- Streamlit is tijdelijk prototype/fallback.
- Next.js wordt de officiële frontend voor productiewaardige workflows.
- API-routes blijven dun: request ontvangen, service aanroepen, response teruggeven.
- Businessregels horen in `services/`, domeinmodules of module-specifieke servicebestanden.
- Statusstrings worden centraal beheerd in `app/backend/domain/statuses.py`.
- De interne productcatalogus is leidend.
- Platformproducten zijn gekoppelde publicaties.
- Bambu Studio blijft verantwoordelijk voor slicing en printvoorbereiding.
- Er worden geen secrets hardcoded opgeslagen.

## Printen via Bambu Studio

De aanbevolen workflow houdt Bambu Cloud, Bambu Handy en Bambu Studio beschikbaar:

1. Koppel op de productdetailpagina een door Bambu Studio voorbereid `.gcode.3mf` bestand.
2. Installeer eenmalig de `Windows-koppeling` op iedere computer waarmee je Bambu Studio wilt openen.
3. Kies `Open direct in Bambu Studio` en sta toe dat de browser de lokale 3D Print Manager-koppeling opent.
4. Kies eerst de productvariant en printer; de app leest de actuele AMS-sleuven en koppelt op materiaal en kleur.
5. De koppeling downloadt en valideert het beveiligde bestand en opent het daarna lokaal in Bambu Studio.
6. Gebruik `Alleen downloaden` als reserveoptie.
7. Bevestig in Bambu Studio de fysieke printer, plate en AMS-toewijzing en kies `Print plate`.
8. Verwerk na afloop het printresultaat in Printplanning.

Een reeds geslicet bestand wordt nooit stilzwijgend naar een ander materiaal of incompatibel printermodel omgezet. De app blokkeert zo'n combinatie en vraagt om opnieuw slicen. De fysieke cloudprinter moet in Bambu Studio bevestigd worden, omdat Bambu Studio hiervoor geen ondersteunde externe koppeling aanbiedt.

Een batchpakket bevat de productielijst, het orderoverzicht, een korte handleiding en alle unieke gekoppelde printbestanden. Direct starten via LAN/MQTT staat apart als geavanceerde modus en is niet nodig voor deze cloudworkflow.
