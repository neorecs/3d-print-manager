# UI-handleiding 3D Print Manager

Deze handleiding legt uit waar je welk scherm voor gebruikt. De applicatie is nu nog een Streamlit-prototype, dus sommige schermen voelen meer als beheerpanelen dan als een volledig afgewerkte webshop-tool.

## Hoofdidee

De app werkt als centrale laag boven je verkoopplatformen en Bambu Studio.

De normale volgorde is:

1. Product aanmaken in de interne catalogus.
2. Varianten toevoegen met SKU, kleur, materiaal, printtijd en filamentverbruik.
3. Productfoto's toevoegen.
4. Platformpublicatie maken voor Etsy, Shopify of later een ander platform.
5. Orders importeren of handmatig aanmaken.
6. Orderregels koppelen via SKU.
7. Voorraad controleren en reserveren.
8. Alleen tekorten naar printplanning sturen.
9. Printresultaat verwerken.
10. Extra gelukte prints naar vrije voorraad boeken.
11. Trends en voorraadadvies gebruiken voor extra productie.

Belangrijk: Bambu Studio blijft voor slicing en printvoorbereiding. Deze app bepaalt vooral wat er geprint moet worden.

## Navigatie

Links in de zijbalk kies je eerst een sectie:

- `Overzicht`: dashboard.
- `Catalogus`: producten, details, foto's en platformpublicaties.
- `Operatie`: orders, voorraad, filament en printplanning.
- `Sturing`: kosten, trends en voorraadadvies.

Daarna kies je de pagina binnen die sectie.

## Dashboard

Gebruik `Dashboard` als startpunt.

Je ziet hier:

- `Vandaag in het kort`: snelle tellingen voor open orders, printtijd, lage voorraad en acties.
- `Procesoverzicht`: de globale route van catalogus naar Bambu-export.
- `Snelle acties`: testdata laden, dummy-orders importeren en voorraadadvies genereren.
- `Orderverwerking`: open orders die nog aandacht nodig hebben.
- `Voorraadadvies`: adviezen om extra producten te printen.
- `Productvoorraad`: producten die onder minimumvoorraad zitten.
- `Publicatiesynchronisatie`: producten waarvan platformpublicaties opnieuw gesynchroniseerd moeten worden.

Praktisch gebruik:

1. Begin op het dashboard.
2. Kijk eerst naar `Orderverwerking`.
3. Kijk daarna naar `Productvoorraad` en `Voorraadadvies`.
4. Gebruik `Snelle acties` alleen voor testen of om dummydata te laden.

## Productcatalogus

Gebruik `Productcatalogus` voor de interne hoofdadministratie van producten.

Dit is de basis. Etsy, Shopify en andere platformen zijn afgeleiden hiervan.

Gebruik dit scherm voor:

- nieuw product aanmaken;
- producttitel en interne naam vastleggen;
- korte en lange omschrijving opslaan;
- verkooptekst opslaan;
- SEO-titel en SEO-omschrijving opslaan;
- producttype en categorie vastleggen;
- productstatus beheren;
- varianten toevoegen.

Productstatussen:

- `concept`: nog in voorbereiding.
- `klaar_voor_publicatie`: product is intern compleet genoeg om te controleren.
- `gepubliceerd`: product is gepubliceerd of bedoeld als actief.
- `gepauzeerd`: tijdelijk niet actief.
- `gearchiveerd`: oud of niet meer actief.

Gebruik `Varianten` voor SKU's. Een variant is bijvoorbeeld:

- dumpling rood PLA;
- dumpling blauw PLA;
- sleutelhanger zwart PETG.

Vul per variant minimaal in:

- SKU;
- kleur;
- materiaal;
- verkoopprijs;
- printtijd;
- filamentgrammen;
- eventueel 3MF/STL-pad.

## Productdetail

Gebruik `Productdetail` wanneer je een bestaand product uitgebreider wilt aanpassen.

Hier beheer je:

- basisinformatie;
- varianten van dat ene product;
- media/foto's;
- tags.

Gebruik dit scherm wanneer:

- je een product later wilt corrigeren;
- je SEO-tekst wilt aanpassen;
- je tags wilt toevoegen of verwijderen;
- je wilt controleren welke varianten bij een product horen.

Let op: als productinformatie wijzigt, kunnen gekoppelde platformpublicaties op `synchronisatie_nodig` komen te staan.

## Productfoto's

Gebruik `Productfoto's` om foto's centraal aan een product te koppelen.

Je kunt:

- foto's uploaden;
- een bestandspad of URL toevoegen;
- alt-tekst invullen;
- volgorde bepalen;
- hoofdfoto kiezen;
- foto's bewerken of verwijderen.

Praktische volgorde:

1. Kies product.
2. Upload of voeg foto toe.
3. Geef alt-tekst mee.
4. Zet de belangrijkste foto als hoofdfoto.
5. Controleer de volgorde.

De centrale foto's kunnen later per platformpublicatie apart geselecteerd worden.

## Platformpublicatie

Gebruik `Platformpublicatie` om een intern product geschikt te maken voor Etsy, Shopify of een ander verkoopplatform.

Dit scherm voelt minder intuïtief omdat het twee dingen tegelijk doet:

- platformen beheren;
- productpublicaties per platform beheren.

### Publicaties

Gebruik het tabblad `Publicaties` voor een specifiek product.

Stappen:

1. Kies bovenaan het product.
2. Maak een nieuwe platformpublicatie aan.
3. Kies platform, bijvoorbeeld Etsy of Shopify.
4. Vul platformtitel, omschrijving, categorie, tags en prijs in.
5. Controleer de publicatie.
6. Kies eventueel platformfoto's.
7. Publiceer, synchroniseer of pauzeer.

Wanneer gebruik je afwijkende velden?

- Etsy heeft vaak kortere tags en andere categorieen nodig.
- Shopify kan andere collecties, typen of omschrijvingen hebben.
- De platformprijs kan afwijken van je interne standaardprijs.

Statussen:

- `niet_gepubliceerd`: bestaat alleen intern.
- `concept`: publicatie is in voorbereiding.
- `klaar_voor_publicatie`: klaar om te controleren/publiceren.
- `gepubliceerd`: gepubliceerd.
- `synchronisatie_nodig`: interne productinformatie is gewijzigd.
- `fout`: laatste publicatie of sync gaf een fout.
- `gepauzeerd`: tijdelijk offline/gepauzeerd.
- `gearchiveerd`: niet meer actief.

### Platformfoto's

Bij een publicatie kun je kiezen welke centrale productfoto's op dat platform gebruikt worden.

Gebruik dit wanneer:

- Etsy andere foto's nodig heeft dan Shopify;
- je een andere eerste foto wilt tonen;
- je per platform een andere volgorde wilt.

### Platformen

Gebruik het tabblad `Platformen` om platformen en connectorgegevens te beheren.

Hier beheer je:

- platformnaam;
- type, bijvoorbeeld Etsy of Shopify;
- API-basis-URL;
- actieve status;
- credentials/tokens.

Voor nu draaien connectors grotendeels in mock/prototype-modus. Sla echte API-tokens pas op wanneer de omgeving goed beveiligd is.

## Orders

Gebruik `Orders` om bestellingen te verwerken.

De belangrijkste volgorde is:

1. Order importeren of aanmaken.
2. Orderregels koppelen via SKU.
3. Voorraad controleren en reserveren.
4. Printtaken maken voor tekorten.
5. Printresultaat verwerken via `Printplanning`.
6. Order verder zetten naar inpakken/verzenden.

### Overzicht

Hier zie je:

- nieuwe orders;
- open orders;
- orders die uit voorraad kunnen;
- orders met printwerk.

Gebruik de orderrij om te zien wat de volgende actie is.

### Detail

Gebruik `Detail` om een specifieke order te verwerken.

Belangrijke knoppen:

- `Orderregels koppelen via SKU`: zoekt interne productvarianten bij orderregels.
- `Voorraad controleren en reserveren`: reserveert beschikbare voorraad.
- `Printtaken maken voor tekorten`: maakt alleen printtaken voor wat ontbreekt.
- `Winst opnieuw berekenen`: berekent geschatte winst.

Belangrijke regel: een orderregel gaat niet automatisch volledig naar printplanning. Eerst wordt voorraad gecontroleerd.

### Nieuw

Gebruik `Nieuw` om handmatig een order en orderregels aan te maken.

Dit is handig voor:

- testorders;
- losse handmatige verkoop;
- orders van een platform dat nog geen connector heeft.

### Import

Gebruik `Import` voor dummy Etsy- of Shopify-import.

Dit maakt testorders aan zodat je de workflow kunt proberen zonder echte platformkoppeling.

## Productvoorraad

Gebruik `Productvoorraad` voor producten die al geprint zijn en klaar liggen.

Dit is niet hetzelfde als filamentvoorraad.

Belangrijke velden:

- `Op voorraad`: hoeveel fysiek klaarligt.
- `Gereserveerd`: hoeveel al voor orders is vastgezet.
- `Vrije voorraad`: op voorraad min gereserveerd.
- `Minimumvoorraad`: grens waaronder het dashboard waarschuwt.
- `Locatie`: waar het product ligt.

Gebruik dit scherm voor:

- voorraad toevoegen;
- voorraad corrigeren;
- gereserveerde aantallen controleren;
- lage voorraad opsporen;
- voorraadbewegingen terugzien.

## Filament

Gebruik `Filament` voor rollen materiaal.

Vul per rol in:

- merk;
- materiaal, bijvoorbeeld PLA, PETG of TPU;
- kleur;
- startgewicht;
- resterend gewicht;
- aankoopprijs;
- minimumgewicht;
- locatie.

De app gebruikt prijs per gram voor kostenberekening.

Gebruik `Filament` wanneer:

- je nieuwe rollen toevoegt;
- je resterend gewicht corrigeert;
- je lage filamentvoorraad wilt herkennen.

## Printplanning

Gebruik `Printplanning` om te bepalen wat geprint moet worden.

### Overzicht

Hier zie je:

- open printtaken;
- actieve/geplande taken;
- totale printtijd;
- filamentverbruik;
- extra voorraadproductie.

Gebruik filters op status en materiaal om sneller batches te maken.

### Uit orders

Gebruik dit nadat je bij `Orders` voorraad hebt gecontroleerd.

De knop maakt of werkt printtaken bij voor ordertekorten.

### Plannen

Gebruik dit om aantallen en status van printtaken aan te passen.

Belangrijk:

- `Aantal nodig`: wat nodig is voor de order of voorraad.
- `Aantal gepland`: wat je echt wilt printen.
- Als gepland hoger is dan nodig, gaat het extra gelukte aantal later naar vrije voorraad.

### Resultaat

Gebruik dit na het printen.

Vul in:

- aantal gelukt;
- aantal mislukt;
- aantal naar order.

De app rekent daarna uit wat naar vrije voorraad gaat.

Voorbeeld:

- nodig voor order: 4;
- gepland: 12;
- gelukt: 11;
- mislukt: 1;
- naar order: 4;
- naar voorraad: 7.

### Batches

Gebruik batches om printtaken te groeperen voor Bambu Studio.

Groeperen kan op:

- materiaal;
- kleur;
- geplande datum;
- geselecteerde printtaken.

Daarna kun je exporteren richting Bambu Studio.

## Kosten en winst

Gebruik `Kosten en winst` om kosteninstellingen en orderwinst te bekijken.

Kosten kunnen bestaan uit:

- filament;
- verpakking;
- platformkosten;
- verzending;
- stroom.

De berekening is bedoeld als schatting, niet als volledige boekhouding.

Gebruik dit scherm wanneer:

- je kosteninstellingen wilt aanpassen;
- je winst per order wilt controleren;
- je wilt zien of een product financieel logisch is.

## Trendanalyse

Gebruik `Trendanalyse` om te zien wat verkoopt.

Je ziet analyses over:

- laatste 30 dagen;
- laatste 60 dagen;
- laatste 90 dagen;
- top producten;
- top kleuren;
- top materialen;
- omzet;
- geschatte winst.

Gebruik dit scherm om te bepalen welke producten vaker op voorraad moeten liggen.

## Voorraadadvies

Gebruik `Voorraadadvies` om te laten berekenen wat verstandig is om extra te printen.

De basisberekening is:

`verwachte verkoop + veiligheidsvoorraad - vrije voorraad = printadvies`

Je kunt advies:

- accepteren;
- aanpassen;
- negeren;
- omzetten naar printtaak.

Praktische volgorde:

1. Genereer advies.
2. Controleer reden en aantallen.
3. Pas aan als je zelf beter weet wat eraan komt.
4. Accepteer of negeer.
5. Zet geaccepteerd advies om naar printtaak.

## Meest gebruikte workflow

Voor dagelijkse orderverwerking:

1. Ga naar `Dashboard`.
2. Controleer `Orderverwerking`.
3. Ga naar `Orders`.
4. Open `Detail`.
5. Koppel orderregels via SKU.
6. Controleer en reserveer voorraad.
7. Maak printtaken voor tekorten.
8. Ga naar `Printplanning`.
9. Plan aantallen.
10. Print in Bambu Studio.
11. Verwerk printresultaat.
12. Controleer productvoorraad.

Voor nieuw product:

1. Ga naar `Productcatalogus`.
2. Maak product aan.
3. Maak varianten aan.
4. Ga naar `Productfoto's`.
5. Upload foto's en kies hoofdfoto.
6. Ga naar `Platformpublicatie`.
7. Maak Etsy/Shopify publicatie aan.
8. Controleer publicatie.
9. Publiceer of synchroniseer.

Voor voorraadproductie:

1. Ga naar `Voorraadadvies`.
2. Genereer advies.
3. Accepteer of pas advies aan.
4. Zet advies om naar printtaak.
5. Ga naar `Printplanning`.
6. Maak batch.
7. Exporteer productielijst.
8. Print via Bambu Studio.
9. Verwerk resultaat.

## Veelvoorkomende verwarring

### Productcatalogus of Platformpublicatie?

Gebruik `Productcatalogus` voor de interne waarheid.

Gebruik `Platformpublicatie` voor hoe dat product op Etsy, Shopify of een ander platform verschijnt.

### Productvoorraad of Filament?

`Productvoorraad` is wat al geprint klaarligt.

`Filament` is materiaal op rol.

### Orders of Printplanning?

`Orders` bepaalt wat klanten besteld hebben en wat uit voorraad kan.

`Printplanning` bepaalt wat daadwerkelijk geprint moet worden.

### Voorraadadvies of Printplanning?

`Voorraadadvies` zegt wat slim is om extra te maken.

`Printplanning` is de daadwerkelijke werklijst voor printen.

### Publiceren of synchroniseren?

`Publiceren` gebruik je voor iets dat nog niet op het platform staat.

`Synchroniseren` gebruik je wanneer het al gekoppeld is en interne informatie gewijzigd is.

## Huidige prototype-beperkingen

- Etsy is nog geen echte live connector.
- Shopify heeft een eerste live basis, maar nog niet alles.
- Dummy-import is bedoeld om de workflow te testen.
- De UI is functioneel, maar nog niet zo intuïtief als een definitieve React/Next.js frontend.
- Bambu Studio wordt niet vervangen.
- Automatisch printen starten is geen onderdeel van deze versie.

