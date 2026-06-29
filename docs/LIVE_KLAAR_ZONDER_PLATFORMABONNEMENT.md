# Live-klaar zonder Etsy/Shopify abonnement

Doel: de 3D Print Manager technisch voorbereiden op echte data zonder nu al betaalde afspraken of live-koppelingen met Etsy/Shopify nodig te hebben.

## Veilig uitgangspunt

- Houd `CONNECTORS_LIVE_MODE=false`.
- Voeg nog geen echte Etsy/Shopify tokens toe als backups en encryptie niet kloppen.
- Producten, voorraad, AI-mockmodus, Bambu-printers, administratie en publicatievelden kunnen wel alvast ingericht worden.
- Echte publicatie, synchronisatie en orderimport worden pas getest wanneer je bewust live modus aanzet.

## Secrets

Zet secrets alleen in de NAS/container environment, niet in Git.

Verplicht voordat echte tokens worden opgeslagen:

- `DATABASE_URL`
- `CREDENTIAL_ENCRYPTION_KEY`
- `CONNECTORS_LIVE_MODE=false`

Optioneel zolang je nog niet live gaat:

- `ETSY_API_KEY`
- `ETSY_ACCESS_TOKEN`
- `ETSY_SHOP_ID`
- `SHOPIFY_ACCESS_TOKEN`
- `SHOPIFY_SHOP_DOMAIN`
- `OPENAI_API_KEY`

Een encryptiesleutel kan via de backend worden gemaakt met:

```text
GET /credentials/generate-key
```

Bewaar deze sleutel buiten Git. Als deze sleutel kwijt is, kunnen opgeslagen platformcredentials niet meer ontsleuteld worden.

## Backup minimale afspraak

Voor live gebruik is minimaal nodig:

- Dagelijkse PostgreSQL dump.
- Backup buiten de actieve container bewaren.
- Retentie van minimaal 14 dagen.
- Minimaal een keer een hersteltest uitvoeren.
- Documenteer waar backups staan en hoe je ze terugzet.

Voorbeeldstrategie op NAS:

```text
/backups/3d-print-manager/
  daily/
  restore-tests/
```

## Hersteltest

Voer voor livegang een test uit:

1. Maak een dump van de huidige database.
2. Start een lege testdatabase.
3. Restore de dump naar die testdatabase.
4. Controleer of producten, orders, voorraad, accounting en printerinstellingen zichtbaar zijn.
5. Noteer datum en resultaat.

## Wanneer pas Etsy/Shopify koppelen?

Pas na deze punten:

- Instellingenpagina toont dat live calls geblokkeerd zijn.
- Credential encryptie is actief.
- Database draait op PostgreSQL.
- Backup bestaat.
- Hersteltest is uitgevoerd.
- Je weet welk platform als eerste echt getest wordt.

Daarna voeg je per platform credentials toe, maar laat je `CONNECTORS_LIVE_MODE=false` totdat je klaar bent voor een bewuste live test.

## Wat kan nu al gratis

- Productcatalogus vullen.
- Productfoto's en varianten voorbereiden.
- Tags, SEO, talen en verkooplanden voorbereiden.
- Voorraad en filament invoeren.
- Printplanning testen.
- Bambu-printers beheren.
- Administratiebasis testen.
- AI Product Assistent in mockmodus gebruiken.
- Etsy/Shopify velden klaarzetten zonder te publiceren.
