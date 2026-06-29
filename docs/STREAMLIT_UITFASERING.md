# Streamlit Uitfasering

Doel: Streamlit blijft tijdelijk fallback, maar Next.js is de officiele frontend. Dit overzicht laat zien welke onderdelen veilig in Next.js zitten en wat nog nodig is voordat Streamlit uit kan.

| Onderdeel | Streamlit | Next.js | Ontbreekt nog in Next.js | Prioriteit |
| --- | --- | --- | --- | --- |
| Dashboard | Ja | Ja | Verdere foutdetails en filters | Middel |
| Producten | Ja | Ja | Bulkacties en verfijnde filters | Middel |
| Productvarianten | Ja | Ja | Snellere variantduplicatie | Laag |
| Productmedia | Ja | Ja | Platform-specifieke fotoselectie verfijnen | Hoog |
| Platformpublicaties | Ja | Ja | Marktkeuze per publicatie en vertaalde payload gebruiken | Hoog |
| Orders | Ja | Ja | Live importcontrole per platform verder detailleren | Hoog |
| Voorraad | Ja | Ja | Extra auditfilters en correctieredenen | Middel |
| Filament | Ja | Ja | Verbruiksoverzicht per periode | Laag |
| Printplanning | Ja | Ja | Batchbewerkingen en exportflow verfijnen | Middel |
| Batches | Ja | Ja | Exportdetails visueel controleren | Middel |
| Analyse/trends | Ja | Ja | Meer periodefilters en productdetailanalyse | Middel |
| Voorraadadvies | Ja | Ja | Adviesacceptatie met aangepaste aantallen verder polijsten | Middel |
| Accounting | Beperkt | Ja | Exportcontrole, btw-regels per land en documentfilters | Hoog |
| Instellingen | Beperkt | Deels | Centrale instellingenpagina ontbreekt nog | Hoog |
| Bambu-printers | Nee/beperkt | Ja | Statusuitlezing stabieler maken | Middel |
| AI Product Assistent | Nee/beperkt | Ja | Echte API-activering, kostenlimiet en promptbeheer | Hoog |

## Veilig uitzetten van Streamlit

Streamlit kan pas uit wanneer deze punten in Next.js voldoende zijn:

1. Productpublicaties kunnen per markt/taal gecontroleerd en gepubliceerd worden.
2. Orderimport en voorraadverwerking zijn betrouwbaar zichtbaar in Next.js.
3. Accounting heeft voldoende export- en controlefuncties voor dagelijks gebruik.
4. Instellingen/secrets/healthchecks zijn centraal vindbaar.
5. Backups en herstelprocedure zijn getest.

## Huidige conclusie

Streamlit nog niet verwijderen. Gebruik Streamlit alleen als fallback/prototype. Bouw nieuwe schermen en verbeteringen direct in Next.js.
