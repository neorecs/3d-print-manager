# Projectcontext

Dit project is aangemaakt binnen Codex onder de naam `3d print manager`.

## Huidige opdracht

De gebruiker wil het verdere projectplan hier aanleveren. Dat plan moet worden gebruikt als leidraad voor de verdere inrichting en ontwikkeling van het project.

## Startpunt

- Projectnaam: 3D Print Manager
- Projectmap: `3d print manager`
- Doel: een applicatie voor het beheren van 3D-printers, printopdrachten, filament, geschiedenis en onderhoud.

## Projectplan

Het volledige projectplan is vastgelegd in `docs/PROJECTPLAN.md`.
Het login- en wereldwijde-toegangspoor is vastgelegd in `docs/PROJECTPLAN_AUTH_LOGIN.md`.

## Eerste ontwikkelfase

Versie 0.1 is opgezet en versie 0.2/0.3/0.4/0.5/0.6/0.7/0.8/0.9/0.10/0.11/0.12 zijn als prototype uitgebreid:

- Docker Compose met PostgreSQL, FastAPI backend en Streamlit frontend.
- Backend los van frontend.
- SQLAlchemy modellen en Alembic migrations.
- Basis API endpoints.
- Dummydata om zonder Etsy/Shopify-koppelingen te kunnen testen.
- Streamlit-dashboard met navigatiepagina's.
- Producten, varianten, filament, media, tags, SEO-velden en extra variantdetails zijn beheerbaar via Streamlit.
- Platformen en productpublicaties zijn beheerbaar via Streamlit, inclusief publicatiecontrole en statusacties.
- Orders en orderregels zijn beheerbaar via Streamlit, inclusief dummy-import en SKU-koppeling naar interne varianten.
- Productvoorraad is gekoppeld aan orders: vrije voorraad wordt berekend, gereserveerd en tekorten worden op orderregels vastgelegd.
- Printplanning maakt taken uit ordertekorten en verwerkt printresultaten terug naar order en vrije voorraad.
- Kosteninstellingen en orderwinstberekening zijn toegevoegd, inclusief filament-, platform-, verpakking-, verzend- en stroomkosten.
- Printbatches kunnen worden geexporteerd naar CSV en Markdown voor gebruik naast Bambu Studio.
- Trendanalyse toont verkoop per variant, top producten, top kleuren, top materialen, omzet, winst en gemiddelde weekverkoop.
- Voorraadadvies berekent aanbevolen printaantallen uit trenddata, vrije voorraad en veiligheidsvoorraad, en kan adviezen omzetten naar printtaken.
- Productwijzigingen markeren relevante platformpublicaties als `synchronisatie_nodig`; publiceren/synchroniseren legt een syncdatum vast.
- Publicatiecontrole is aangescherpt met Etsy- en Shopify-specifieke checks en betere foutweergave in Streamlit.
- De eerste v1.0-basis voor platformconnectors is toegevoegd: mockmodus, connectorstatus, credentialbeheer en publish/sync via connectorresultaten.
- Er is een `unittest` suite toegevoegd voor voorraadreservering, printresultaten, publicatievalidatie/mockpublicatie en voorraadadvies.
- De publishing-logica is uit `api/routes.py` gehaald naar `app/backend/publishing/service.py`, zodat publicatievalidatie, sync-markering en connectorcalls als domeinservice beheerd worden.
- De inventory/order-voorraadlogica is uit `api/routes.py` gehaald naar `app/backend/inventory/service.py`, inclusief SKU-koppeling, ordervoorraadcontrole, vrije voorraad, reserveren, vrijgeven en voorraadcorrecties.
- De acceptatiecriteria voor versie 1.0 zijn uitgewerkt in `docs/ACCEPTATIECHECKLIST.md` met status `klaar`, `deels klaar` of `open`.
- Productfoto-upload is toegevoegd: afbeeldingen worden lokaal opgeslagen onder `app/backend/uploads/`, statisch geserveerd via `/uploads/...` en in Streamlit als preview getoond.
- Platform-specifieke fotoselectie is toegevoegd via `product_publication_media`, inclusief Alembic migration `0003_publication_media` en Streamlit-beheer onder Platformpublicatie.
- Voorraadadvies kan nu handmatig worden aangepast voordat het wordt geaccepteerd of omgezet naar een printtaak; tests controleren dat het aangepaste aantal wordt gebruikt.
- Platformcredentials worden nu met Fernet versleuteld opgeslagen via `CREDENTIAL_ENCRYPTION_KEY`; API/Streamlit tonen geen geheime waarde terug.
- Shopify live connector is gestart met Admin GraphQL API `2026-04`: `productCreate` voor publicatie en `productUpdate` voor synchronisatie. Bulkvarianten, voorraad-sync en orderimport staan nog open.
