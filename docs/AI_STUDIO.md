# AI-studio

Te vinden op elk product: tabblad **AI-studio** (teksten) en **Foto's → Bewerk met AI** (foto's).

## Teksten per verkoopkanaal

1. Kies de kanalen (standaard de kanalen waar het product al een publicatie heeft).
2. **Teksten maken**: de AI krijgt de productgegevens, de regels van elk kanaal (titellengte,
   aantal tags, taglengte, stijl) en maximaal 4 foto's (originele foto's eerst).
3. Klopt iets niet met de kanaalregels, dan krijgt de AI één herstelronde; daarna kort de app
   zelf in wat nog te lang is.
4. Pas de tekst aan waar nodig en klik **Overnemen**: titel, omschrijving en tags gaan naar de
   publicatie(s) van dat kanaal. Voor Marktplaats en Vinted gebruik je daarna het plaatsingspakket.

Zonder AI-sleutel krijg je voorbeeldteksten uit de productgegevens, zodat je de werkwijze kunt proberen.

## Foto's bewerken

Kies een stijl (witte achtergrond, lichte studio, woonkamer, buiten) en klik **Bewerk met AI**.
Het resultaat wordt een **nieuwe** foto met het label *AI-bewerkt*; het origineel blijft staan.
Etsy eist minstens één onbewerkte foto van het echte product, en kopers moeten zien wat ze krijgen.

## Instellingen (Dockhand)

| Variabele | Standaard | Betekenis |
| --- | --- | --- |
| `AI_OPENAI_ENABLED` | `false` | Zet op `true` om echte AI te gebruiken. |
| `OPENAI_API_KEY` | – | Je OpenAI API-sleutel (API-tegoed, los van ChatGPT Plus). |
| `OPENAI_PRODUCT_MODEL` | `gpt-5.4-mini` | Model voor teksten. |
| `AI_DAILY_REQUEST_LIMIT` | `20` | Maximum tekstaanvragen per dag (een herstelronde telt mee). |
| `OPENAI_IMAGE_MODEL` | `gpt-image-2.6-sunburst` | Model voor fotobewerking. `gpt-image-2.6-flare` is sneller en goedkoper. |
| `OPENAI_IMAGE_QUALITY` | `medium` | `low`, `medium` of `high`. |
| `AI_DAILY_IMAGE_LIMIT` | `10` | Maximum fotobewerkingen per dag, apart van de tekstlimiet. |
