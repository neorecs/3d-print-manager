# Streamlit Uitfasering

Doel: Streamlit blijft tijdelijk fallback, maar Next.js is de officiele frontend. Dit document volgt alleen de schermmigratie. Functionele open punten en livegangacceptatie staan uitsluitend in `ACCEPTATIECHECKLIST.md`.

| Onderdeel | Streamlit | Next.js | Migratiestatus | Prioriteit |
| --- | --- | --- | --- | --- |
| Dashboard | Ja | Ja | Hoofdscherm gemigreerd | Laag |
| Producten | Ja | Ja | Dagelijkse workflow gemigreerd | Laag |
| Productvarianten | Ja | Ja | Beheer gemigreerd | Laag |
| Productmedia | Ja | Ja | Upload en platformselectie gemigreerd | Laag |
| Platformpublicaties | Ja | Ja | Beheer gemigreerd; liveacceptatie staat in de hoofdchecklist | Middel |
| Orders | Ja | Ja | Overzicht, detail en importbediening gemigreerd | Laag |
| Voorraad | Ja | Ja | Overzicht en productbeheer gemigreerd | Laag |
| Filament | Ja | Ja | Beheer gemigreerd | Laag |
| Printplanning | Ja | Ja | Taken en resultaatverwerking gemigreerd | Laag |
| Batches | Ja | Ja | Batchbeheer en export gemigreerd | Laag |
| Analyse/trends | Ja | Ja | Bestaande datagestuurde onderdelen gemigreerd | Middel |
| Voorraadadvies | Ja | Ja | Beheer gemigreerd; UX-verfijning staat in de hoofdchecklist | Middel |
| Accounting | Beperkt | Ja | Bestaande administratiefunctionaliteit gemigreerd | Middel |
| Instellingen | Beperkt | Ja | Gebruikers, veiligheid en livegereedheid staan in Next.js | Laag |
| Bambu-printers | Nee/beperkt | Ja | Printerbeheer en Studio-workflow staan in Next.js | Laag |
| AI Product Assistent | Nee/beperkt | Ja | Mock- en gecontroleerde AI-flow staan in Next.js | Laag |

## Veilig uitzetten van Streamlit

Streamlit kan uit wanneer deze operationele voorwaarden zijn bevestigd:

1. De gebruiker heeft de dagelijkse product-, order-, voorraad- en printworkflow uitsluitend in Next.js geaccepteerd.
2. Er is gedurende een afgesproken proefperiode geen Streamlit-only handeling nodig geweest.
3. Beheer van credentials, gebruikers, healthchecks en herstel is bereikbaar buiten Streamlit.
4. Voor verwijdering is een backup gemaakt en is in Git vastgelegd welke container en route verdwijnen.

## Huidige conclusie

Alle bekende hoofdschermen bestaan in Next.js. Streamlit nog niet verwijderen totdat de operationele proef hierboven is afgerond; bouw geen nieuwe functionaliteit meer in Streamlit.
