# Modeladvies voor de resterende auditstappen

Dit document legt vast welk model het best past bij de resterende punten uit `ANALYSE_2026-09-11.md`. Het advies is praktisch: GPT-5.6 Sol voert de meeste codewijzigingen uit; GPT-6 Astra wordt alleen ingezet als extra controle bij grote risico's of de definitieve livegang.

Het advies volgt de positionering in de [officiele OpenAI-modeldocumentatie](https://developers.openai.com/api/docs/models): een sterk professioneel werkmodel voor de uitvoering en het meest capabele model alleen voor de zwaarste controles. Modelnamen en beschikbaarheid kunnen later veranderen; actualiseer dit document dan opnieuw.

Actuele stand op 13 september 2026: 23 van 25 auditpunten zijn in code afgerond. Punt 23 is voltooid en lokaal geverifieerd: voorraadadvies is uitlegbaar, gebruikt actuele voorraad bij acties en kan niet dubbel worden omgezet. GitHub Actions-run `34748789329` stond bij vastlegging nog in de wachtrij. De echte Etsy-proef en fiscale go/no-go blijven gereserveerd voor een gerichte GPT-6 Astra-review. Punt 24 is de aanbevolen volgende implementatiestap met GPT-5.6 Luna.

| Punt | Onderwerp | Aanbevolen model | Reden |
| --- | --- | --- | --- |
| 12 | Datavolume en prestaties | GPT-5.6 Sol | Uitgevoerd met Sol op 12 september 2026; server-side paginering, aggregaties en volumetests zijn groen in run `34699454229` |
| 13 | Verkoop en administratieketen | GPT-5.6 Sol + GPT-6 Astra-review | Sol-implementatie gereed in run `34700837763`; Astra blijft nodig voor echte platform- en financiele go/no-go |
| 14 | Integratie- en browsertests | GPT-5.6 Sol | Uitgevoerd met Sol op 12 september 2026; PostgreSQL- en browserketen zijn groen in GitHub Actions-run `34686176416` |
| 15 | Lokale configuratie en herstel | GPT-5.6 Sol + GPT-6 Astra-review | Uitgevoerd met Sol op 12 september 2026; gezamenlijke restore is groen, Astra-review volgt bij de definitieve livegangcontrole |
| 16 | Documentatie en placeholders | GPT-5.6 Luna | Uitgevoerd op 12 september 2026; leidende bewijschecklist en eerlijke scherminhoud zijn groen in run `34701798060` |
| 19 | Context behouden bij doorklikken | GPT-5.6 Sol | Uitgevoerd met Sol op 13 september 2026; contextnavigatie en browsertest zijn groen in run `34746258994` |
| 20 | Gemeten versus geschatte gegevens | GPT-5.6 Sol | Uitgevoerd met Sol op 13 september 2026; presentatiehelpers en mobiele browsertest zijn groen in run `34747173348` |
| 23 | Analyse en voorraadadviezen | GPT-5.6 Sol | Uitgevoerd met Sol op 13 september 2026; uitlegbare en actuele adviezen plus mobiele gebruikersstroom zijn lokaal groen, run `34748789329` wacht nog op GitHub |
| 24 | Tegenstrijdige livegangadviezen | GPT-5.6 Luna | Documentatie opschonen en een leidende checklist aanwijzen |
| 25 | Dagelijks werk boven configuratie | GPT-5.6 Sol | Brede UX-wijziging over meerdere dagelijkse werkprocessen |

## Gebruik van GPT-6 Astra

GPT-6 Astra is niet nodig voor iedere implementatiestap. Gebruik het voor:

1. een gerichte review van punt 13 en 15;
2. de definitieve beveiligings-, gegevens- en livegangaudit;
3. onvoorziene problemen waarbij meerdere modules tegelijk geraakt worden.

Zo blijft GPT-5.6 Sol het standaardmodel voor degelijk ontwikkelwerk en wordt het duurdere/zwaardere model alleen gebruikt waar de extra controle aantoonbaar waarde heeft.
