# Meldingen en achtergrondworker

De service `worker` in `docker-compose.next-nas.yml` haalt elke 5 minuten nieuwe orders op bij alle actieve Etsy- en Shopify-kanalen en stuurt bij elke nieuwe order een melding naar je telefoon. Hij werkt volledig vanuit je eigen netwerk: er hoeft niets open te staan op internet.

- Orders worden alleen opgehaald als `CONNECTORS_LIVE_MODE=true`.
- Elke order geeft precies één melding per kanaal, ook als hij later opnieuw wordt geïmporteerd.
- Een mislukte import geeft maximaal één waarschuwing per kanaal per dag.
- Mislukte meldingen worden tot 3 keer opnieuw geprobeerd.
- In de melding staan kanaal, ordernummer, producten en bedrag, plus een link naar de order. Geen klantnaam of adres.
- **Instellingen** toont of de worker de afgelopen 30 minuten heeft gedraaid en welke meldingskanalen actief zijn, met een knop "Testmelding sturen".

## Kies een meldingskanaal

### Telegram

1. Open Telegram en stuur `/newbot` naar **@BotFather**. Kies een naam; je krijgt een token.
2. Stuur je nieuwe bot een willekeurig bericht.
3. Open `https://api.telegram.org/bot<token>/getUpdates` in een browser en zoek `"chat":{"id":...}`. Dat getal is je chat-ID.
4. Zet in Dockhand:

```env
TELEGRAM_BOT_TOKEN=<token van BotFather>
TELEGRAM_CHAT_ID=<chat-ID>
```

### ntfy

1. Installeer de ntfy-app en abonneer je op een onderwerp met een **lange willekeurige naam** (iedereen die de naam kent, kan meelezen).
2. Zet in Dockhand:

```env
NTFY_URL=https://ntfy.sh/<lange-willekeurige-naam>
```

Gebruik je een eigen ntfy-server met toegangsbeheer, zet dan ook `NTFY_TOKEN`.

Je kunt ook beide kanalen tegelijk instellen.

## Overige instellingen

| Variabele | Standaard | Betekenis |
| --- | --- | --- |
| `APP_PUBLIC_URL` | `http://10.5.1.150:38502` | Adres van de app; wordt gebruikt voor de link in de melding. |
| `WORKER_INTERVAL_SECONDS` | `300` | Tijd tussen twee rondes (minimaal 60). |
| `WORKER_AUTO_PROCESS_ORDERS` | `false` | Op `true`: nieuwe orders worden meteen verwerkt (voorraad reserveren, printtaken maken, conceptboeking). |
| `WORKER_SYNC_INVENTORY` | `false` | Op `true`: na elke ronde de voorraad naar Shopify sturen. |

Ook zonder worker kun je orders met de hand ophalen via **Orders → Orders ophalen**. Beide gebruiken dezelfde import, die onthoudt tot waar de vorige import kwam.
