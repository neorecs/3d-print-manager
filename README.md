# 3D Print Manager

Centrale beheerlaag voor 3D-printactiviteiten: producten, platformpublicaties, orders, productvoorraad, filament, printplanning, trends, voorraadadvies en exports richting Bambu Studio.

## Status

Versie 0.12 prototype:

- FastAPI backend
- PostgreSQL database
- SQLAlchemy modellen
- Alembic migration
- Streamlit dashboard/prototype
- Next.js frontend in opbouw onder `app/frontend_next`
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
- Bambu Studio-export maken als CSV en Markdown
- Productielijst exporteren met ordernummer, aantallen, kleur, materiaal en printbestandpad
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

Uploads worden lokaal opgeslagen onder `app/backend/uploads/` en via de API geserveerd onder `/uploads/...`. Deze map staat in `.gitignore`.

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

De Next.js frontend gebruikt de FastAPI backend via:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:38080
```

Streamlit blijft beschikbaar tot de belangrijkste schermen zijn gemigreerd naar Next.js.

## NAS Next.js stack

`docker-compose.next-nas.yml` draait de Next.js frontend samen met een private Git-managed backendservice. Die backend publiceert geen eigen poort en is bedoeld voor de nieuwe Next.js UI. De oudere publieke backend op poort `38080` kan tijdelijk blijven bestaan voor bestaande links en fallback-schermen.

Voor NAS-deploy zijn minimaal deze environment variables nodig in Dockhand:

```env
DATABASE_URL=
CREDENTIAL_ENCRYPTION_KEY=
```

Zet secrets niet in Git. De Next.js service gebruikt intern standaard `http://backend:8000`.

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

De huidige suite controleert:

- voorraadreservering en alleen tekort naar printplanning;
- printresultaten verwerken naar order, vrije voorraad en afgekeurde prints;
- publicatievalidatie en mock-publicatie via de connectorlaag;
- voorraadadvies op basis van verkoop, veiligheidsvoorraad en vrije voorraad.

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
    models/
    schemas/
    services/
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
- De interne productcatalogus is leidend.
- Platformproducten zijn gekoppelde publicaties.
- Bambu Studio blijft verantwoordelijk voor slicing en printvoorbereiding.
- Er worden geen secrets hardcoded opgeslagen.
