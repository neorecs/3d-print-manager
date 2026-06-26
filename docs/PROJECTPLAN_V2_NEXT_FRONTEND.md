# Projectplan V2 - 3D Print Manager naar professionele SaaS-app

## Doel

De 3D Print Manager moet doorgroeien van een werkend Streamlit-prototype naar een professioneel intern SaaS-dashboard voor een kleine 3D-print onderneming.

De backend blijft de centrale basis:

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Docker Compose

De frontendstrategie verandert:

- Streamlit blijft tijdelijk beschikbaar als prototype/fallback.
- Nieuwe officiële frontend wordt `frontend_next` met React/Next.js.
- Nieuwe schermen worden waar mogelijk direct in Next.js gebouwd.
- Streamlit wordt later uitgefaseerd zodra de belangrijkste workflows in Next.js werken.

## Waarom niet verder polijsten in Streamlit

Streamlit is bruikbaar voor snelle prototypes en eenvoudige dashboards, maar dit project groeit naar een echte workflow-app met:

- veel tabellen;
- productfoto's;
- publicatiechecklists;
- orderworkflow;
- printplanning;
- AI-productassistent;
- platformkoppelingen;
- later mogelijk gebruikersrollen;
- betere mobiele bediening.

Voor deze doelen is React/Next.js beter geschikt.

## Huidige status

Aanwezig:

- FastAPI-backend met gescheiden API.
- PostgreSQL datamodel voor producten, platformen, orders, voorraad, filament, printplanning, kosten, trends en voorraadadvies.
- Streamlit-dashboard met veel prototypefunctionaliteit.
- Next.js frontend als nieuwe hoofdinterface met dashboard, catalogus, productdetail, orders, printplanning, filament, productvoorraad, verkoopkanalen, analyse en AI Product Assistent.
- Dummydata.
- Voorraadregels en printplanning-businessregels.
- Shopify/Etsy connectorbasis.
- AI Product Assistent in mockmodus.
- Lokale implementatie voor OpenAI `gpt-5.4-mini`, nog niet live op NAS.
- GitHub repository gevuld: `neorecs/3d-print-manager`.

Nog belangrijk:

- NAS-deployproces werkt via GitHub/Dockhand, maar moet nog verder worden gedocumenteerd en van healthchecks/backups worden voorzien.
- Streamlit-container is eerder handmatig gepatcht.
- Echte AI is nog niet live geactiveerd.
- Echte Etsy/Shopify liveflows zijn nog niet productiehard.

## Voortgang bijgewerkt op 2026-06-26

Next.js bevat nu de eerste werkbare versies van:

- Dashboard;
- Productcatalogus;
- Product aanmaken;
- Productdetail;
- Variantenbeheer;
- Fotobeheer/media;
- Productpublicaties;
- Productvoorraad per product;
- Centraal productvoorraad-overzicht op `/voorraad`;
- Verkoopkanalen/platformbeheer op `/verkoopkanalen`;
- Orders en orderdetail;
- Printplanning, printresultaten, batches en Bambu-exportknop;
- Filamentbeheer;
- Analyse, trends en voorraadadvies op `/analyse`;
- AI Product Assistent op `/catalogus/ai-assistent` met gratis mockmodus en veilige echte-AI statuscontrole.

Daarmee zijn de grootste UI-gaten uit de V2-migratie nu voorzien van een eerste Next.js-scherm. De resterende V2-focus verschuift naar verfijning, productiehardheid, echte connectoren, credentials, healthchecks, backups en het gecontroleerd uitfaseren van Streamlit.

## Architectuurdoel

```text
FastAPI backend
  |
  | REST API
  v
Next.js frontend

Streamlit frontend
  |
  | tijdelijk prototype/fallback
  v
uitfaseren zodra Next.js voldoende compleet is
```

## Nieuwe mappenstructuur

Gewenste toevoeging:

```text
app/
  frontend_next/
    app/
    components/
    lib/
    styles/
    types/
    public/
    package.json
    next.config.js
    tsconfig.json
```

Streamlit blijft voorlopig:

```text
app/frontend_streamlit/
```

## Fase 1 - Fundament Next.js

Doel: nieuwe frontend technisch opzetten zonder bestaande werking te breken.

Taken:

1. `app/frontend_next` aanmaken.
2. Next.js + TypeScript installeren.
3. Tailwind CSS instellen.
4. Basis layout maken:
   - sidebar;
   - topbar;
   - contentgebied;
   - responsive basis.
5. API-client maken voor FastAPI.
6. Centrale types maken voor:
   - product;
   - variant;
   - platform;
   - order;
   - inventory;
   - print job;
   - recommendation.
7. `.env.example` uitbreiden met Next.js frontendvariabelen.
8. Docker Compose uitbreiden met optionele `frontend_next` service.
9. Streamlit naast Next.js laten bestaan.

Acceptatie:

- Next.js start lokaal.
- Next.js kan `/health` van backend uitlezen.
- Docker Compose kan backend, database, Streamlit en Next.js draaien.
- Geen bestaande backendtests breken.

## Fase 2 - Design system

Doel: professionele SaaS-look vastleggen voordat schermen worden gebouwd.

Componenten:

- `AppShell`
- `Sidebar`
- `Topbar`
- `PageHeader`
- `MetricCard`
- `StatusBadge`
- `SectionCard`
- `DataTable`
- `EmptyState`
- `ActionButton`
- `WorkflowSteps`
- `Checklist`
- `WarningBox`
- `SuccessBox`

Stijl:

- rustige lichte achtergrond;
- zakelijke kaarten;
- duidelijke statuskleuren;
- geen drukke gradients;
- Nederlandse labels;
- duidelijke witruimte;
- consistente knoppen.

Acceptatie:

- Dashboard kan gebouwd worden zonder losse ad-hoc CSS.
- Statussen hebben herkenbare badges.
- Tabellen hebben nette headers, spacing en acties.

## Fase 3 - Nieuw Dashboard

Doel: centrale startpagina bouwen in Next.js.

Dashboard toont:

- open orders;
- orders volledig uit voorraad;
- orders met printtekort;
- open printtaken;
- geschatte printtijd;
- lage productvoorraad;
- lage filamentvoorraad;
- publicaties met synchronisatie nodig;
- geschatte omzet;
- geschatte winst;
- belangrijkste voorraadadviezen.

Blokken:

- Vandaag afhandelen
- Printplanning
- Voorraadadvies
- Publicaties met aandacht nodig

Acceptatie:

- Dashboard voelt als professioneel beheerplatform.
- Gebruiker ziet meteen wat aandacht nodig heeft.
- Geen technische kolommen zichtbaar in hoofdweergave.

## Fase 4 - Catalogus in Next.js

Doel: productbeheer migreren naar professionele workflow.

Schermen:

1. Productoverzicht
2. Productdetail
3. Varianten
4. Foto's/media
5. Tags
6. AI Product Assistent

Productdetail tabs:

1. Basisinformatie
2. Varianten
3. Foto's
4. Verkoopteksten
5. Publicaties
6. Voorraad
7. Analyse

Acceptatie:

- Producten kunnen bekeken en aangemaakt worden.
- Productdetail is geen lange formulierpagina meer.
- AI Product Assistent is duidelijk gescheiden in mockmodus en echte AI-modus.

Status 2026-06-26:

- Eerste Next.js versie aanwezig voor productoverzicht, product aanmaken, productdetail, varianten, media, publicaties, productvoorraad en AI Product Assistent.
- Nog verfijnen: tags als eigen beheerblok, verkoopteksten als aparte sectie/tab, analyse per product en compactere tabnavigatie.

## Fase 5 - Verkoopkanalen

Doel: multichannelbeheer overzichtelijk maken.

Schermen:

- Platformen
- Publicaties
- Synchronisatiestatus
- Publicatiecontrole
- Credentials/status

Publicatiechecklist:

- titel ingevuld;
- omschrijving ingevuld;
- prijs ingevuld;
- categorie ingevuld;
- tags ingevuld;
- foto gekozen;
- SKU gekoppeld;
- verzendprofiel ingevuld;
- klaar voor publicatie.

Acceptatie:

- Per product is duidelijk wat klaar is voor Etsy/Shopify.
- Synchronisatie nodig is visueel herkenbaar.
- Fouten zijn duidelijk en niet verstopt.

Status 2026-06-26:

- Eerste Next.js versie aanwezig op `/verkoopkanalen`.
- Platformen kunnen worden aangemaakt en aangepast.
- Connectorstatus, ontbrekende credentials, sync-acties en publicatiefouten zijn zichtbaar.
- Nog verfijnen: credentials invoeren/beheren vanuit de UI, platformdetailpagina, echte live testflows.

## Fase 6 - Orders

Doel: orderverwerking praktischer maken.

Schermen:

- Orderoverzicht
- Orderdetail
- Handmatige order
- Importstatus

Workflow:

1. Order ontvangen
2. Orderregels gekoppeld
3. Voorraad gecontroleerd
4. Voorraad gereserveerd
5. Printtaken aangemaakt
6. Printresultaat verwerkt
7. Klaar voor verzending
8. Afgerond

Acceptatie:

- Volgende logische actie is per order zichtbaar.
- Orderregels tonen voorraadstatus en printstatus.
- Winstberekening is bereikbaar vanuit orderdetail.

## Fase 7 - Voorraad en filament

Doel: productvoorraad en filament duidelijk scheiden.

Schermen:

- Productvoorraad
- Voorraadbewegingen
- Filamentrollen

Statussen:

- voldoende;
- laag;
- tekort;
- gereserveerd;
- vrije voorraad.

Acceptatie:

- Vrije voorraad is direct zichtbaar.
- Gereserveerd en op voorraad worden niet door elkaar gehaald.
- Filament toont resterend gewicht en prijs per gram.

Status 2026-06-26:

- Eerste Next.js versie aanwezig voor productvoorraad op `/voorraad`.
- Voorraadregels tonen op voorraad, gereserveerd, vrije voorraad, minimum, status en locatie.
- Voorraadbewegingen zijn zichtbaar.
- Filamentrollen zijn aanwezig op `/filament` met resterend gewicht, minimum en prijs per gram.
- Nog verfijnen: centrale voorraadcorrecties vanuit `/voorraad`, filters, zoeken, voorraadbeweging-detail.

## Fase 8 - Printplanning

Doel: printplanning als productiebord.

Schermen:

- Open printtaken
- Geplande printtaken
- Batches
- Printresultaten
- Bambu-export

Groeperingen:

- materiaal;
- kleur;
- geplande datum;
- batch;
- order;
- voorraadproductie.

Acceptatie:

- Batchoverzicht toont kleur, materiaal, aantallen, printtijd en filament.
- Export richting Bambu Studio blijft beschikbaar.
- Printresultaten kunnen verwerkt worden.

## Fase 9 - Analyse en advies

Doel: managementgerichte inzichten.

Schermen:

- Kosten en winst
- Trends
- Voorraadadvies

Toon:

- omzet;
- kosten;
- winst;
- margepercentage;
- top producten;
- top kleuren;
- top materialen;
- uitlegbaar voorraadadvies.

Acceptatie:

- Voorraadadvies toont concrete reden.
- Kosten/winst is begrijpelijk zonder technische velden.

Status 2026-06-26:

- Eerste Next.js versie aanwezig op `/analyse`.
- Toont top producten, top kleuren, top materialen, omzet, geschatte winst, marge-indicatie, kosteninstellingen en voorraadadvies.
- Voorraadadvies kan worden gegenereerd, geaccepteerd, genegeerd of omgezet naar printtaak.
- Nog verfijnen: betere periodekeuze, grafieken, orderwinstdetail en marge per platform.

## Fase 10 - Echte AI Product Assistent

Doel: OpenAI `gpt-5.4-mini` veilig activeren.

Voorwaarden:

- `AI_OPENAI_ENABLED=false` blijft standaard.
- `OPENAI_API_KEY` alleen in backend environment.
- Frontend praat nooit rechtstreeks met OpenAI.
- Duidelijke kostenwaarschuwing in UI.
- Daglimiet of gebruiksteller toevoegen voordat echte AI breed gebruikt wordt.

Taken:

1. Lokale implementatie controleren.
2. Backend endpoint live deployen.
3. Statusendpoint tonen in Next.js.
4. Echte AI-knop alleen activeren als backend `ready=true` meldt.
5. Kostenlimiet toevoegen.

Acceptatie:

- Mockmodus blijft gratis beschikbaar.
- Echte AI werkt alleen na expliciete configuratie.
- Geen OpenAI-key in GitHub.

Status 2026-06-26:

- Eerste Next.js versie aanwezig op `/catalogus/ai-assistent`.
- UI toont of echte AI klaarstaat of gratis mockmodus actief is.
- Frontend praat niet rechtstreeks met OpenAI.
- Mockmodus maakt gratis productconcepten zonder API-call.
- Nog verfijnen: concept omzetten naar echt product, daglimiet/gebruiksregistratie, echte AI pas activeren na expliciete productieconfiguratie.

## Fase 11 - NAS en deploy verbeteren

Doel: geen handmatige containerpatches meer.

Taken:

1. Docker Compose opschonen.
2. Backend image rebuild betrouwbaar maken.
3. Frontend Next.js image toevoegen.
4. Streamlit image tijdelijk behouden.
5. NAS Dockhand deployproces documenteren.
6. Healthchecks toevoegen:
   - backend;
   - frontend_next;
   - streamlit;
   - database.
7. Backupstrategie documenteren.

Acceptatie:

- Nieuwe code komt via GitHub/NAS-deploy live.
- Geen handmatige edits in containers nodig.
- Healthchecks zijn groen na deploy.

## Fase 12 - Live connectoren

Doel: richting echte verkoopplatformen.

Eerst:

- Shopify orderimport;
- Shopify product/variant sync uitbreiden;
- Etsy OAuth/tokenbeheer;
- Etsy orderimport;
- Etsy productpublicatie.

Niet tegelijk met UI-migratie bouwen. Eerst frontendbasis stabiel maken.

Acceptatie:

- Tokens veilig opgeslagen.
- Connectorfouten worden gelogd.
- Import/sync kan getest worden zonder echte publicatiefouten.

## Niet doen in V2

- Backend herschrijven.
- Database onnodig wijzigen.
- Streamlit direct verwijderen.
- Printerbesturing bouwen.
- Eigen slicer bouwen.
- Geheime sleutels committen.
- Alles tegelijk migreren.

## Werkvolgorde voor Codex

Aanbevolen volgorde:

1. `frontend_next` scaffolden.
2. Design system bouwen.
3. Dashboard bouwen.
4. Productcatalogus bouwen.
5. AI Product Assistent migreren.
6. Verkoopkanalen bouwen.
7. Orders bouwen.
8. Voorraad bouwen.
9. Printplanning bouwen.
10. Analyse bouwen.
11. Streamlit uitfaseren.
12. Live connectoren afronden.

Bijgewerkte eerstvolgende werkvolgorde vanaf 2026-06-26:

1. UI-verfijning en filters voor `/voorraad`, `/verkoopkanalen`, `/analyse` en `/catalogus/ai-assistent`.
2. Credentialsbeheer en secrets-scherm voor verkoopkanalen.
3. Productconcept uit AI-assistent kunnen opslaan als conceptproduct.
4. Winstberekening beter zichtbaar maken op orderdetail en analyse.
5. NAS healthchecks, backupstrategie en deploydocumentatie afronden.
6. Daarna pas echte Shopify/Etsy liveflows productiehard maken.

## Beslisregel Streamlit vs Next.js

Nieuwe complexe workflowschermen worden in Next.js gebouwd.

Streamlit alleen nog gebruiken voor:

- tijdelijke fallback;
- prototypecontrole;
- snelle interne debugschermen.

Als een scherm productiewaardig moet voelen, gaat het naar Next.js.

## Tests per fase

Altijd minimaal:

```bash
python -m py_compile app/backend/api/routes.py app/backend/core/config.py app/backend/schemas/common.py
python -m py_compile app/frontend_streamlit/streamlit_app.py
```

Bij backendwijzigingen:

```bash
docker compose exec -T backend python -m unittest discover -s tests -v
```

Bij Next.js:

```bash
npm run lint
npm run build
```

Bij Docker/NAS:

- backend healthcheck;
- frontend healthcheck;
- database healthcheck;
- basispagina openen.

## Eerste concrete opdracht

Start met fase 1 en 2:

1. Maak `app/frontend_next`.
2. Scaffold Next.js + TypeScript.
3. Voeg Tailwind of vergelijkbare centrale styling toe.
4. Maak `AppShell`, `Sidebar`, `Topbar`, `PageHeader`, `MetricCard`, `StatusBadge`, `SectionCard`.
5. Maak API-client voor FastAPI.
6. Bouw eerste Dashboard-pagina met echte backenddata.
7. Laat Streamlit ongemoeid als fallback.
8. Werk README bij met de nieuwe frontend.
