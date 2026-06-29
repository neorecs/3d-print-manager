# Acceptatiechecklist versie 1.0

Statussen:

- `klaar`: werkt in het huidige prototype.
- `deels klaar`: basis is aanwezig, maar nog niet volledig of nog mock/prototype.
- `open`: nog niet gebouwd.

| Nr | Acceptatiecriterium | Status | Opmerking |
| --- | --- | --- | --- |
| 1 | Ik producten kan aanmaken. | klaar | Producten kunnen via API en Streamlit worden aangemaakt. |
| 2 | Ik productinformatie centraal kan beheren. | deels klaar | Basisvelden, SEO, verkooptekst en status zijn aanwezig; workflow kan nog verfijnd worden. |
| 3 | Ik productfoto's kan toevoegen. | klaar | Foto-upload naar lokale backend-opslag en mediarecords zijn aanwezig. |
| 4 | Ik een hoofdfoto kan kiezen. | klaar | `is_primary` is aanwezig en beheerbaar. |
| 5 | Ik productvarianten met kleur, materiaal, printtijd en filamentverbruik kan vastleggen. | klaar | Varianten ondersteunen kleur, materiaal, printtijd en filamentgrammen. |
| 6 | Ik per platform afwijkende titel, omschrijving, tags, categorie en prijs kan beheren. | klaar | Productpublicaties hebben platform-specifieke velden. |
| 7 | Ik producten naar Etsy kan publiceren of synchroniseren. | deels klaar | Mockconnector werkt; eerste live draft-listing/sync basis is aanwezig maar moet met echte Etsy OAuth/scopes en taxonomy getest worden. |
| 8 | Ik producten naar Shopify kan publiceren of synchroniseren. | deels klaar | Live GraphQL productCreate/productUpdate, bulkvarianten en variantlink-opslag zijn aanwezig; echte live-test blijft nodig. |
| 9 | Ik filamentrollen kan beheren. | klaar | Filamentrollen, resterend gewicht en prijs per gram zijn aanwezig. |
| 10 | Ik productvoorraad kan beheren. | klaar | Productvoorraad, vrije voorraad en voorraadbewegingen zijn aanwezig. |
| 11 | Ik orders uit Etsy en Shopify kan importeren. | deels klaar | Shopify live-capable import met paginering is aanwezig; Etsy heeft eerste connectorbasis en mockimport. Echte tokens/scopes moeten live getest worden. |
| 12 | Orderregels automatisch gekoppeld kunnen worden aan interne producten. | klaar | SKU-koppeling naar interne varianten is aanwezig. |
| 13 | De applicatie automatisch controleert of een order uit voorraad geleverd kan worden. | klaar | Ordervoorraadcontrole is gebouwd en getest. |
| 14 | Alleen het tekort automatisch naar printplanning gaat. | klaar | `quantity_to_print` wordt alleen voor tekort gezet; test aanwezig. |
| 15 | Ik meer kan printen dan nodig is voor een order. | klaar | `quantity_planned` kan hoger zijn dan orderbehoefte. |
| 16 | Extra gelukte prints automatisch aan vrije voorraad toegevoegd kunnen worden. | klaar | Printresultaat boekt overschot naar productvoorraad; test aanwezig. |
| 17 | Mislukte prints geregistreerd kunnen worden. | klaar | Mislukte aantallen worden als `afgekeurd` voorraadbeweging geregistreerd. |
| 18 | Elke voorraadwijziging traceerbaar is. | deels klaar | Belangrijke voorraadwijzigingen maken movements; verdere auditvelden/user tracking en platform-sync-logdetail kunnen nog sterker. |
| 19 | De applicatie kosten en winst per order kan berekenen. | klaar | Orderwinstberekening met kosteninstellingen is aanwezig. |
| 20 | De applicatie printtaken kan groeperen op kleur en materiaal. | deels klaar | Printbatches bevatten kleur/materiaal; automatische batchoptimalisatie kan nog beter. |
| 21 | De applicatie een productielijst voor Bambu Studio kan exporteren. | klaar | CSV en Markdown export per batch is aanwezig. |
| 22 | De applicatie verkooptrends kan tonen. | klaar | Trendanalyse over 30/60/90 dagen is aanwezig. |
| 23 | De applicatie advies kan geven welke producten extra geprint moeten worden. | klaar | Voorraadadvies wordt berekend uit verkoop, vrije voorraad en veiligheidsvoorraad. |
| 24 | Ik een voorraadadvies kan accepteren, aanpassen of negeren. | klaar | Aanpassen, accepteren en negeren zijn aanwezig. |
| 25 | Een geaccepteerd voorraadadvies kan worden omgezet naar printtaken. | klaar | Conversie naar printtaak is aanwezig. |
| 26 | De applicatie kan tonen welke producten opnieuw gesynchroniseerd moeten worden met verkoopplatformen. | klaar | Productwijzigingen zetten publicaties op `synchronisatie_nodig`. |
| 27 | De basis werkt via een Streamlit-dashboard. | klaar | Streamlit bestaat nog als prototype/fallback; Next.js is inmiddels de hoofdinterface. |
| 28 | De backend is los genoeg om later een betere frontend te bouwen. | klaar | Backend en Next.js frontend zijn gescheiden; verdere service-splitsing kan later, maar de architectuur is bruikbaar. |

Extra projectplanregel: platform-specifieke fotoselectie en fotovolgorde is aanwezig via `product_publication_media`.

## Samenvatting

- Klaar: 21
- Deels klaar: 7
- Open: 0

Belangrijk: meerdere `deels klaar` punten zijn functioneel als prototype, maar tellen nog niet als echte v1.0 omdat Etsy/Shopify liveflows met echte credentials en scopes nog gecontroleerd getest moeten worden.

## Belangrijkste open werk richting echte v1.0

1. PostgreSQL backup na NAS-deploy controleren.
2. Restore-test uitvoeren en resultaat noteren.
3. Echte Etsy connector live testen en aanvullen: OAuth/tokenverversing, taxonomyvelden, productfoto-upload en orderimportdetails.
4. Shopify live testen met echte credentials: productpublicatie, bulkvarianten, orderimport en voorraad-sync.
5. Vaste productiekey instellen buiten Docker Compose fallback voordat echte tokens worden opgeslagen.
6. Verdere service-splitsing voor planning, analytics, costs en exports.
7. Meer testdekking voor API-endpoints, exports, kostenberekening en connectorfouten.

## Livegangstatus 2026-06-29

- Next.js is de hoofdinterface.
- Dashboardkaarten klikken door naar de juiste werkmodules.
- NAS Next.js compose heeft backend- en frontend-healthchecks.
- NAS Next.js compose heeft een `postgres_backup` service voor dagelijkse PostgreSQL dumps.
- V1.0 livegang-runbook is toegevoegd in `docs/V1_LIVEGANG_RUNBOOK.md`.
- Connectoren blijven standaard veilig in mockmodus.
- Nog niet live-klaar voor echte platformorders: backup moet na deploy gecontroleerd worden en restore-test ontbreekt nog.
