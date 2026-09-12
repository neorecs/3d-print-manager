# Modeladvies voor de resterende auditstappen

Dit document legt vast welk model het best past bij de resterende punten uit `ANALYSE_2026-09-11.md`. Het advies is praktisch: GPT-5.6 Sol voert de meeste codewijzigingen uit; GPT-6 Astra wordt alleen ingezet als extra controle bij grote risico's of de definitieve livegang.

| Punt | Onderwerp | Aanbevolen model | Reden |
| --- | --- | --- | --- |
| 12 | Datavolume en prestaties | GPT-5.6 Sol | Gericht meten, API-query's verbeteren en regressietests schrijven |
| 13 | Verkoop en administratieketen | GPT-5.6 Sol + GPT-6 Astra-review | Sol voor implementatie; Astra voor de laatste controle van platform- en financiële risico's |
| 14 | Integratie- en browsertests | GPT-5.6 Sol | Testinfrastructuur en gelijktijdigheid vragen nauwkeurige codeanalyse; uitgevoerd met Sol |
| 15 | Lokale configuratie en herstel | GPT-5.6 Sol + GPT-6 Astra-review | Sol voor inrichting; Astra voor een laatste herstel- en livegangcontrole |
| 16 | Documentatie en placeholders | GPT-5.6 Luna | Beperkt risico en vooral tekstuele, goed controleerbare wijzigingen |
| 19 | Context behouden bij doorklikken | GPT-5.6 Sol | Frontendstatus en navigatie moeten betrouwbaar samen blijven werken |
| 20 | Gemeten versus geschatte gegevens | GPT-5.6 Sol | Vereist controle van databetekenis in backend en UI |
| 23 | Analyse en voorraadadviezen | GPT-5.6 Sol | Berekeningen moeten uitlegbaar en met tests aantoonbaar zijn |
| 24 | Tegenstrijdige livegangadviezen | GPT-5.6 Luna | Documentatie opschonen en een leidende checklist aanwijzen |
| 25 | Dagelijks werk boven configuratie | GPT-5.6 Sol | Brede UX-wijziging over meerdere dagelijkse werkprocessen |

## Gebruik van GPT-6 Astra

GPT-6 Astra is niet nodig voor iedere implementatiestap. Gebruik het voor:

1. een gerichte review van punt 13 en 15;
2. de definitieve beveiligings-, gegevens- en livegangaudit;
3. onvoorziene problemen waarbij meerdere modules tegelijk geraakt worden.

Zo blijft GPT-5.6 Sol het standaardmodel voor degelijk ontwikkelwerk en wordt het duurdere/zwaardere model alleen gebruikt waar de extra controle aantoonbaar waarde heeft.
