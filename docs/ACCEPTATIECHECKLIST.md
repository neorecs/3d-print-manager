# Leidende acceptatiechecklist versie 1.0

Bijgewerkt: 12 september 2026.

Dit is de enige leidende bron voor de actuele v1.0-status. Projectplannen en audits leggen ontwerp en historie vast, maar bepalen niet of een onderdeel operationeel is geaccepteerd.

## Betekenis van de kolommen

- **Gebouwd**: de functionaliteit bestaat in de huidige code.
- **Automatisch getest**: relevante backend-, frontend- of ketentests bestaan en zijn groen.
- **NAS getest**: het gedrag is op de NAS zichtbaar of handmatig beproefd. `Niet vastgelegd` betekent niet dat het niet werkt, maar dat bewijs ontbreekt.
- **Operationeel geaccepteerd**: de volledige praktijkworkflow is door de gebruiker bevestigd. Externe platformflows tellen pas na een proef met echte credentials.

| Nr | Acceptatiecriterium | Gebouwd | Automatisch getest | NAS getest | Operationeel geaccepteerd | Bewijs of resterende controle |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Producten aanmaken | Ja | Ja | Ja | Ja | Next.js-catalogus en product-API |
| 2 | Productinformatie centraal beheren | Ja | Ja | Ja | Deels | Dagelijkse invoerflow wordt nog verder vereenvoudigd |
| 3 | Productfoto's toevoegen | Ja | Ja | Niet vastgelegd | Proef nodig | Upload, opslag en mediarecord zijn getest |
| 4 | Hoofdfoto kiezen | Ja | Ja | Niet vastgelegd | Proef nodig | Eén hoofdfoto wordt afgedwongen |
| 5 | Varianten met kleur, materiaal, printtijd en filament beheren | Ja | Ja | Ja | Deels | Praktijkcontrole met meer producten blijft nuttig |
| 6 | Afwijkende platformtitel, omschrijving, tags, categorie en prijs beheren | Ja | Ja | Ja | Deels | Echte platformpayload nog niet geaccepteerd |
| 7 | Publiceren en synchroniseren naar Etsy | Ja | Gesimuleerd | Nee | Nee | Echte OAuth, scopes, taxonomy en conceptlisting testen |
| 8 | Publiceren en synchroniseren naar Shopify | Ja | Gesimuleerd | Nee | Nee | Echte credentials, scopes, varianten en voorraad-sync testen |
| 9 | Filamentrollen beheren | Ja | Ja | Ja | Deels | Dagelijkse UX wordt nog verbeterd |
| 10 | Productvoorraad beheren | Ja | Ja | Ja | Deels | Correctie- en reserveringsflow breder beproeven |
| 11 | Orders uit Etsy en Shopify importeren | Ja | Gesimuleerd | Nee | Nee | Per platform een gecontroleerde live-import uitvoeren |
| 12 | Orderregels via SKU aan interne producten koppelen | Ja | Ja | Niet vastgelegd | Proef nodig | Import- en ordertests dekken de koppeling |
| 13 | Voorraad automatisch voor een order controleren | Ja | Ja | Niet vastgelegd | Proef nodig | PostgreSQL-concurrency en herverwerking zijn getest |
| 14 | Alleen het voorraadtekort naar printplanning sturen | Ja | Ja | Niet vastgelegd | Proef nodig | Planningtests dekken volledig, gedeeltelijk en geen voorraad |
| 15 | Meer plannen dan de order nodig heeft | Ja | Ja | Niet vastgelegd | Proef nodig | `quantity_planned` ondersteunt overproductie |
| 16 | Extra gelukte prints naar vrije voorraad boeken | Ja | Ja | Niet vastgelegd | Proef nodig | Printresultaattests dekken voorraadboeking |
| 17 | Mislukte prints registreren | Ja | Ja | Niet vastgelegd | Proef nodig | Afgekeurde aantallen krijgen een voorraadbeweging |
| 18 | Iedere voorraadwijziging traceerbaar maken | Deels | Ja | Niet vastgelegd | Nee | Bewegingslog bestaat; actor/auditdetail is nog niet overal gelijk |
| 19 | Kosten en winst per order berekenen | Ja | Ja | Niet vastgelegd | Proef nodig | Fiscale juistheid moet apart worden beoordeeld |
| 20 | Printtaken groeperen op kleur en materiaal | Ja | Ja | Niet vastgelegd | Proef nodig | Batches groeperen; optimalisatie is geen v1.0-blokkade |
| 21 | Productielijst voor Bambu Studio exporteren | Ja | Ja | Ja | Deels | Studio-openworkflow is bevestigd; volledige batchdag nog beproeven |
| 22 | Verkooptrends tonen | Ja | Ja | Niet vastgelegd | Proef nodig | Alleen werkelijk aangesloten grafieken gelden als gebouwd |
| 23 | Voorraadadvies berekenen | Ja | Ja | Niet vastgelegd | Proef nodig | Actuele voorraadcontrole en uitleg worden nog aangescherpt |
| 24 | Advies accepteren, aanpassen of negeren | Ja | Ja | Niet vastgelegd | Proef nodig | Afgehandelde adviezen moeten duidelijker uit de werkvoorraad |
| 25 | Geaccepteerd advies omzetten naar printtaak | Ja | Ja | Niet vastgelegd | Proef nodig | Herhaalactie en actuele voorraad opnieuw controleren |
| 26 | Tonen welke platformpublicaties synchronisatie nodig hebben | Ja | Ja | Ja | Deels | Echte synchronisatie blijft platformafhankelijk |
| 27 | Basis werkt via een Streamlit-dashboard | Ja | Deels | Ja | Ja | Streamlit blijft fallback; Next.js is de officiele hoofdinterface |
| 28 | Backend en frontend los van elkaar houden | Ja | Ja | Ja | Ja | FastAPI en Next.js zijn afzonderlijke services |

Platformspecifieke fotoselectie en fotovolgorde bestaan via `product_publication_media`.

## V1.0-besluit

- **Intern gebruik:** mogelijk, mits productiekeys zijn ingesteld en de actuele backup/herstelcontrole groen is.
- **Etsy live:** nog niet geaccepteerd; eerst één gecontroleerde OAuth-, conceptpublicatie- en orderimportproef.
- **Shopify live:** nog niet geaccepteerd; eerst één gecontroleerde publicatie-, varianten-, voorraad- en orderimportproef.
- **Administratie:** bruikbaar als beheer- en exporthulpmiddel, nog geen vervanging voor fiscale controle.
- **Externe toegang:** HTTPS en certificaat blijven uitgesteld tot een eigen domein wordt gebruikt.

Gebruik voor de concrete go/no-go-volgorde `docs/V1_LIVEGANG_RUNBOOK.md`. Bewijs van een test moet daar of in deze checklist met datum worden vastgelegd voordat `Operationeel geaccepteerd` op `Ja` wordt gezet.
