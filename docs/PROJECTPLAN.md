# Projectplan - 3D Print Order, Inventory, Planning & Product Manager

## Doel

Bouw een centrale beheerapplicatie voor 3D-printactiviteiten. De applicatie beheert producten, productfoto's, publicaties naar verkoopplatformen, orders, productvoorraad, filamentvoorraad, printplanning, kosten, winst, trendanalyse, voorraadadvies en exports richting Bambu Studio.

## Belangrijke uitgangspunten

- Bouw geen eigen slicer.
- Vervang Bambu Studio niet.
- Bambu Studio blijft verantwoordelijk voor slicing, printvoorbereiding en werken met 3MF/STL-bestanden.
- Deze applicatie is de centrale beheerlaag boven Bambu Studio.
- De interne productcatalogus is leidend.
- Platformproducten zijn gekoppelde publicaties van interne producten.
- Bouw modulair, zodat Streamlit later vervangen kan worden door React/Next.js of een andere frontend.
- Sla geen secrets hardcoded op.

## Technische voorkeur

- Python
- FastAPI backend
- PostgreSQL database
- Docker Compose
- SQLAlchemy
- Alembic migrations
- Streamlit als eerste dashboard/prototype

## Gewenste modules

- Platformmodule voor Etsy, Shopify en later WooCommerce/eBay.
- Centrale productcatalogus met media, varianten, SEO, prijzen en platformpublicaties.
- Ordermodule met import, orderregels en voorraadcontrole.
- Productvoorraadmodule met reserveringen en voorraadbewegingen.
- Filamentvoorraadmodule met rollen, materiaal, kleur en kosten per gram.
- Printplanningmodule met printtaken, batches en resultaatverwerking.
- Kosten- en winstmargemodule.
- Administratiemodule voor verkoopboek, inkoopboek, documenten/bonnen, btw-controle en export voor boekhouder.
- Trendanalyse en voorraadadvies.
- Export richting Bambu Studio.

## Businessregels

1. Een orderregel mag niet automatisch volledig naar printplanning gaan; eerst moet productvoorraad worden gecontroleerd.
2. Beschikbare voorraad is `op voorraad - gereserveerd`.
3. Als er genoeg vrije voorraad is, wordt de orderregel volledig uit voorraad gereserveerd.
4. Als er deels voorraad is, wordt dat deel gereserveerd en wordt alleen het tekort een printtaak.
5. Als er geen voorraad is, wordt de volledige orderregel een printtaak.
6. Extra gelukte prints gaan naar vrije productvoorraad.
7. Mislukte prints mogen niet aan voorraad worden toegevoegd.
8. Elke voorraadwijziging krijgt een `inventory_movement`.
9. Trendanalyse moet uitlegbaar blijven.
10. Voorraadadvies moet kunnen worden geaccepteerd, aangepast of genegeerd.
11. De interne productcatalogus is leidend.
12. Producten mogen alleen gepubliceerd worden als verplichte velden gevuld zijn.
13. Platformpublicatie vereist ook verplichte platformvelden.
14. Per platform mogen titel, omschrijving, categorie, tags en prijs afwijken.
15. Foto's worden centraal beheerd, met platformselectie en volgorde.
16. Productwijzigingen moeten synchronisatiebehoefte tonen.
17. De gebruiker kiest of wijzigingen direct worden doorgestuurd of alleen intern opgeslagen.
18. Bouw geen eigen slicer.
19. Vervang Bambu Studio niet.
20. Automatische printstart is geen onderdeel van versie 1.
21. Administratie is een hulpmiddel voor volledigheid, traceerbaarheid en export; fiscale keuzes moeten controleerbaar blijven en kunnen later door een boekhouder/fiscalist worden beoordeeld.
22. Boekhoudkundige correcties mogen later niet stil worden overschreven; gebruik correctieregels of creditfacturen.

## Versieplanning

- 0.1: basisstructuur, Docker Compose, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Streamlit, dummydata.
- 0.2: producten en filament.
- 0.3: uitgebreide productcatalogus.
- 0.4: platformpublicaties.
- 0.5: orders.
- 0.6: productvoorraad.
- 0.7: printplanning.
- 0.8: kosten en winst.
- 0.9: export voor Bambu Studio.
- 0.10: trendanalyse.
- 0.11: voorraadadvies.
- 0.12: publicatie en synchronisatie.
- 0.13: administratiebasis met verkoopboek, inkoopboek, documenten en btw-overzicht.
- 1.0: werkbare eerste versie met echte Etsy- en Shopify-connectors.

## Versie 0.1 scope

Maak:

- Docker Compose met PostgreSQL en backend.
- FastAPI backend.
- Databaseconnectie.
- SQLAlchemy modellen voor de gevraagde tabellen.
- Alembic migrations.
- Basis API endpoints.
- Streamlit dashboard met navigatiepagina's.
- Dummydata voor testen zonder echte platformkoppelingen.
- README met lokale startinstructies.
