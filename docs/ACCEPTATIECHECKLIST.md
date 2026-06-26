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
| 7 | Ik producten naar Etsy kan publiceren of synchroniseren. | deels klaar | Mockconnector werkt; echte Etsy API-publicatie is nog open. |
| 8 | Ik producten naar Shopify kan publiceren of synchroniseren. | deels klaar | Live GraphQL productCreate/productUpdate is aanwezig; bulkvarianten, voorraad-sync en orderimport ontbreken nog. |
| 9 | Ik filamentrollen kan beheren. | klaar | Filamentrollen, resterend gewicht en prijs per gram zijn aanwezig. |
| 10 | Ik productvoorraad kan beheren. | klaar | Productvoorraad, vrije voorraad en voorraadbewegingen zijn aanwezig. |
| 11 | Ik orders uit Etsy en Shopify kan importeren. | deels klaar | Dummy-import werkt; echte API-import is nog open. |
| 12 | Orderregels automatisch gekoppeld kunnen worden aan interne producten. | klaar | SKU-koppeling naar interne varianten is aanwezig. |
| 13 | De applicatie automatisch controleert of een order uit voorraad geleverd kan worden. | klaar | Ordervoorraadcontrole is gebouwd en getest. |
| 14 | Alleen het tekort automatisch naar printplanning gaat. | klaar | `quantity_to_print` wordt alleen voor tekort gezet; test aanwezig. |
| 15 | Ik meer kan printen dan nodig is voor een order. | klaar | `quantity_planned` kan hoger zijn dan orderbehoefte. |
| 16 | Extra gelukte prints automatisch aan vrije voorraad toegevoegd kunnen worden. | klaar | Printresultaat boekt overschot naar productvoorraad; test aanwezig. |
| 17 | Mislukte prints geregistreerd kunnen worden. | klaar | Mislukte aantallen worden als `afgekeurd` voorraadbeweging geregistreerd. |
| 18 | Elke voorraadwijziging traceerbaar is. | deels klaar | Belangrijke voorraadwijzigingen maken movements; verdere auditvelden/user tracking ontbreken nog. |
| 19 | De applicatie kosten en winst per order kan berekenen. | klaar | Orderwinstberekening met kosteninstellingen is aanwezig. |
| 20 | De applicatie printtaken kan groeperen op kleur en materiaal. | deels klaar | Printbatches bevatten kleur/materiaal; automatische batchoptimalisatie kan nog beter. |
| 21 | De applicatie een productielijst voor Bambu Studio kan exporteren. | klaar | CSV en Markdown export per batch is aanwezig. |
| 22 | De applicatie verkooptrends kan tonen. | klaar | Trendanalyse over 30/60/90 dagen is aanwezig. |
| 23 | De applicatie advies kan geven welke producten extra geprint moeten worden. | klaar | Voorraadadvies wordt berekend uit verkoop, vrije voorraad en veiligheidsvoorraad. |
| 24 | Ik een voorraadadvies kan accepteren, aanpassen of negeren. | klaar | Aanpassen, accepteren en negeren zijn aanwezig. |
| 25 | Een geaccepteerd voorraadadvies kan worden omgezet naar printtaken. | klaar | Conversie naar printtaak is aanwezig. |
| 26 | De applicatie kan tonen welke producten opnieuw gesynchroniseerd moeten worden met verkoopplatformen. | klaar | Productwijzigingen zetten publicaties op `synchronisatie_nodig`. |
| 27 | De basis werkt via een Streamlit-dashboard. | klaar | Streamlit-dashboard draait op poort `38501`. |
| 28 | De backend is los genoeg om later een betere frontend te bouwen. | deels klaar | Backend en frontend zijn gescheiden; verdere service-splitsing en API-contracten kunnen nog sterker. |

Extra projectplanregel: platform-specifieke fotoselectie en fotovolgorde is aanwezig via `product_publication_media`.

## Samenvatting

- Klaar: 20
- Deels klaar: 8
- Open: 0

Belangrijk: meerdere `deels klaar` punten zijn functioneel als prototype, maar tellen nog niet als echte v1.0 omdat Etsy/Shopify nog mock zijn en enkele workflows nog niet productiehard zijn.

## Belangrijkste open werk richting echte v1.0

1. Echte Etsy connector: OAuth/tokenbeheer, productpublicatie, synchronisatie en orderimport.
2. Shopify connector uitbreiden met bulkvarianten, voorraad-sync en echte orderimport.
3. Vaste productiekey instellen buiten Docker Compose fallback voordat echte tokens worden opgeslagen.
4. Verdere service-splitsing voor planning, analytics, costs en exports.
5. Meer testdekking voor API-endpoints, exports, kostenberekening en connectorfouten.
