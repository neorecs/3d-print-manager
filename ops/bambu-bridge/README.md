# Bambu bridge: printers op een andere locatie

Bambu's LAN-modus werkt alleen binnen het netwerk van de printer. Voor printers op een
andere plek (bij familie, een tweede werkplaats) draai je daar deze kleine bridge.

```
printer  <-- MQTT/FTPS (lokaal) -->  bridge  -- HTTPS (uitgaand) -->  3D Print Manager
```

De bridge maakt alleen een **uitgaande** HTTPS-verbinding met de app. Op die locatie hoef je
dus niets open te zetten in de router.

## Wat je nodig hebt

- Een computer die altijd aan staat in het netwerk van de printers: een NAS, Raspberry Pi of mini-pc.
- De printers in **LAN-modus met Developer Mode** aan (zoals voor printers in je eigen netwerk).
- De app moet via **HTTPS** bereikbaar zijn vanaf die locatie, bijvoorbeeld via een reverse proxy
  of Cloudflare Tunnel. Alleen `/api/bridge-agent/` hoeft van buitenaf bereikbaar te zijn.

## Instellen

1. In de app: **Printers → Printerbeheer → Bridge aanmaken**. Je krijgt één keer een token (`pmb_…`).
2. Zet deze map (`ops/bambu-bridge`) op de computer op die locatie en start:

   ```bash
   BRIDGE_APP_URL=https://jouw-domein BRIDGE_TOKEN=pmb_... docker compose up -d --build
   ```

   Zonder Docker kan het ook: `pip install "paho-mqtt>=2,<3"` en dan
   `BRIDGE_APP_URL=... BRIDGE_TOKEN=... python3 bridge.py` (bijvoorbeeld als systemd-service).
3. Voeg in de app de printer toe met verbinding **Andere locatie (via bridge)**, kies de bridge
   en vul het lokale IP-adres (zoals de printer het daar heeft), het serienummer en de access code in.

Binnen ongeveer 10 seconden staat de bridge op *online* en verschijnt de printerstatus.

## Wat kan via de bridge

- Live status: printerstatus, voortgang, temperaturen, AMS.
- Pauzeren, hervatten en stoppen.
- Een print starten met het gekoppelde printbestand. De bridge haalt het bestand op, zet het via
  FTPS op de printer en start de print. Vlak voor de start controleert de bridge nog zelf of de
  printer vrij is. Een printstart die geen bevestiging kreeg, wordt nooit vanzelf opnieuw geprobeerd.

## Veiligheid

- De token wordt in de app alleen als hash opgeslagen. Kwijt of gelekt? Trek de bridge in en maak een nieuwe.
- Printergegevens (IP, serienummer, access code) beheer je in de app. De bridge krijgt ze via de
  versleutelde HTTPS-verbinding en houdt ze alleen in het geheugen.
- De bridge weigert te starten met een adres dat niet met `https://` begint.

## Instellingen

| Variabele | Standaard | Betekenis |
| --- | --- | --- |
| `BRIDGE_APP_URL` | – | Adres van de app, met `https://`. |
| `BRIDGE_TOKEN` | – | Token van de bridge (`pmb_…`). |
| `BRIDGE_POLL_SECONDS` | door de app bepaald (10) | Hoe vaak de bridge synchroniseert. |
| `BRIDGE_LOG_LEVEL` | `INFO` | `DEBUG` voor meer details. |
