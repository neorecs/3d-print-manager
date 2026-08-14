# Audit: 13 aanbevelingen

Status na uitvoering van de UX- en code-audit.

| Nr. | Maatregel | Uitvoering |
| --- | --- | --- |
| 1 | Backend niet publiek vertrouwen | Interne tokencontrole op alle backendroutes; NAS-backend heeft geen publieke poort. |
| 2 | Gebruikersrechten backendmatig afdwingen | Iedere beschermde aanvraag vereist een door Next.js ondertekende sessie; admin-, operator- en viewerrechten worden centraal gecontroleerd. |
| 3 | Sessies intrekbaar maken | `session_version` wordt gecontroleerd en verhoogd bij wachtwoord-, rol-, status- en MFA-wijzigingen. |
| 4 | Loginmisbruik duurzaam begrenzen | Loginmislukkingen worden in de database gelogd en begrensd, dus niet alleen in tijdelijk frontendgeheugen. |
| 5 | Bestanden afschermen | De publieke uploadmount is verwijderd; downloads lopen via gecontroleerde routes met padvalidatie. |
| 6 | Voorraad volledig traceerbaar maken | Ook aanmaken en handmatig bewerken schrijft movements met gebruiker, bron, reden en voor/na-standen. |
| 7 | Gelijktijdige voorraad- en printacties beveiligen | Kritieke regels worden vergrendeld; negatieve vrije voorraad en te grote vrijgave worden geweigerd; herverwerking is getest. |
| 8 | Boekhouding exact en afsluitbaar maken | Decimal/centafronding, configureerbaar btw-tarief, afgesloten perioden en dubbele-boekingbeveiliging zijn toegevoegd. |
| 9 | Dashboard echte data laten tonen | Demo-indicatoren zijn vervangen door orders, orderregels, varianten en printerstatus uit de backend; alle blokken klikken door. |
| 10 | Trage catalogusaanvragen verminderen | Publicaties worden in een totaalendpoint opgehaald en producten/orders zijn in de UI gepagineerd. |
| 11 | Navigatie en mobiel gebruik verbeteren | Dubbele navigatie is verwijderd, mobiele bediening gebruikt een compact menu en lange labels breken binnen hun vak. |
| 12 | Productieconfiguratie verharden | Backend zonder reload, meerdere workers, browserbeveiligingsheaders, geen publieke API-URL en geen uitgeschakelde npm-TLS-controle. |
| 13 | Automatische kwaliteitscontrole toevoegen | Volledige backendtests, frontendproductiebouw, login-rooktest en een CI-workflow zijn toegevoegd. |

## Liveganggrens

De readiness-pagina blijft externe livegang blokkeren zolang HTTPS/secure cookies, recente backups en een hersteltest niet aantoonbaar actief zijn. Dit is bewust: lokaal gebruik via HTTP blijft mogelijk, maar de app meldt dan niet ten onrechte dat internetpublicatie veilig is.
