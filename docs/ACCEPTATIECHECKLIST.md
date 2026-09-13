# Leidende acceptatiechecklist versie 1.0

Bijgewerkt: 13 september 2026.

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
| 9 | Filamentrollen beheren | Ja | Ja | Ja | Deels | Bestaande rollen staan voor toevoegen; read-only op NAS gecontroleerd op 13 september 2026 |
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
| 23 | Voorraadadvies berekenen | Ja | Ja | Niet vastgelegd | Proef nodig | Periode, reden, berekentijd en actuele vrije voorraad zijn zichtbaar |
| 24 | Advies accepteren, aanpassen of negeren | Ja | Ja | Niet vastgelegd | Proef nodig | Actieve adviezen en historie zijn gescheiden |
| 25 | Geaccepteerd advies omzetten naar printtaak | Ja | Ja | Niet vastgelegd | Proef nodig | Actuele voorraad wordt hercontroleerd en dubbele omzetting is geblokkeerd |
| 26 | Tonen welke platformpublicaties synchronisatie nodig hebben | Ja | Ja | Ja | Deels | Status en gewone koppelingslabels read-only op NAS gecontroleerd; echte synchronisatie blijft platformafhankelijk |
| 27 | Basis werkt via een Streamlit-dashboard | Ja | Deels | Ja | Ja | Streamlit blijft fallback; Next.js is de officiele hoofdinterface |
| 28 | Backend en frontend los van elkaar houden | Ja | Ja | Ja | Ja | FastAPI en Next.js zijn afzonderlijke services |

Platformspecifieke fotoselectie en fotovolgorde bestaan via `product_publication_media`.

## NAS UX-controle 13 september 2026

- Functionele versie `bfd074e` is via Dockhand uitgerold; frontend, backend, database en worker waren gezond.
- Orders toont eerst filters en bestaande testorders, daarna pas ophalen en ingeklapte geavanceerde importinstellingen.
- Filament toont de bestaande rol voor het ingeklapte formulier om een nieuwe rol toe te voegen.
- Verkoopkanalen toont eerst koppelingsstatus en publicaties met aandacht; instellingen zijn ingeklapt en interne veldnamen zijn vervangen door Nederlandse labels.
- Administratie toont de bon-/inkoopactie voor periode- en fiscale instellingen; fiscale instellingen, periodeafsluiting en handmatige verkoop zijn ingeklapt.
- De controle was alleen-lezen. Testorders, omzet, voorraad, filament en administratieregels zijn niet gewijzigd.

## NAS testdata-opruiming 13 september 2026

- Vooraf is een verse PostgreSQL-backup gemaakt: `print_manager_20260913T193925Z.dump`; de SHA-256-controle is geslaagd.
- De drie expliciet geselecteerde testorders `ORD-2026-0001`, `SHOPIFY-2-MOCK-SHOPIFY-1001` en `ETSY-1-MOCK-ETSY-1001` zijn transactioneel verwijderd.
- Alleen directe afgeleiden zijn opgeruimd: drie orderregels, ordergebonden voorraadmutaties, een nog niet gestarte printtaak en een winstberekening. Er waren geen definitieve boekhoudverkopen.
- Zes gereserveerde producten zijn vrijgegeven. De fysieke voorraad bleef zes en de gereserveerde voorraad is nu nul.
- Nacontrole: nul orders, nul euro orderomzet en nul ordergebonden printtaken. Producten, filament, printers en gebruikers zijn behouden.
- De secretrotatie is op verzoek overgeslagen. De eerder vastgestelde historische blootstelling blijft daarom een open beveiligingsrisico en mag niet als opgelost worden aangemerkt.

## V1.0-besluit

- **Intern gebruik op het vertrouwde lokale netwerk:** mogelijk zodra Instellingen geen interne blokkades toont. Recente database- en bestandsbackups plus een productiehersteltest tellen mee; platformversleuteling is pas nodig als echte platformtokens worden opgeslagen.
- **Echte platformtokens opslaan:** mogelijk zodra Instellingen `Opslag klaar` toont. Houd de koppelingen in veilige teststand en voer gegevens alleen in via het vertrouwde lokale netwerk zolang HTTPS is uitgesteld.
- **Etsy live:** nog niet geaccepteerd; eerst één gecontroleerde OAuth-, conceptpublicatie- en orderimportproef.
- **Shopify live:** nog niet geaccepteerd; eerst één gecontroleerde publicatie-, varianten-, voorraad- en orderimportproef.
- **Administratie:** bruikbaar als beheer- en exporthulpmiddel, nog geen vervanging voor fiscale controle.
- **Toegang tot de website via internet:** bewust uitgesteld. Een domein, HTTPS, secure cookies en een afzonderlijke externe beveiligingscontrole zijn eerst vereist. Dit blokkeert lokaal gebruik en uitgaande platformkoppelingen niet.

## Bewijsbronnen

- Deze checklist is de enige leidende bron voor de functionele en operationele v1.0-acceptatie.
- Het scherm **Instellingen** toont de actuele technische toestand van de draaiende omgeving en de geregistreerde tijdstippen van backups en hersteltest.
- GitHub Actions bewijst de geisoleerde technische herstelketen, maar is geen bewijs dat de actuele NAS-productiebackup is teruggezet.
- `V1_LIVEGANG_RUNBOOK.md` beschrijft de procedure; het overschrijft geen ontbrekend runtime- of gebruikersbewijs met een groen label.

Gebruik voor de concrete go/no-go-volgorde `docs/V1_LIVEGANG_RUNBOOK.md`. Bewijs van een test moet daar of in deze checklist met datum worden vastgelegd voordat `Operationeel geaccepteerd` op `Ja` wordt gezet.
