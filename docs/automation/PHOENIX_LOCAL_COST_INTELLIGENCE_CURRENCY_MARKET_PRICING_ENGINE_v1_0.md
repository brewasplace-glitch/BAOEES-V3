# Phoenix Local Cost Intelligence, Currency & Market Pricing Engine v1.0

## Doel

Phoenix moet voor iedere kostencalculatie de projectgeografie als uitgangspunt nemen:

`projectlocatie -> land/gebiedsdeel -> lokale valuta -> lokale prijsbron -> actuele peildatum -> kostenregel`

## Harde regels

1. De UI-taal bepaalt nooit het projectland of de valuta.
2. Valuta mag alleen volgen uit expliciete of later gevalideerde projectgeografie.
3. Prijsselectie volgt: **stad -> regio -> land**.
4. Een regionaal/stedelijk prijsboek mag niet als nationaal prijsboek worden gebruikt wanneer de projectregio/-plaats onbekend is.
5. Iedere prijsbron moet land, valuta, bron, peildatum/effective date en echte prijsregels bevatten.
6. Een `valid_until`-venster mag aantonen dat een officieel prijsboek nog geldig is; anders geldt de freshnesslimiet.
7. Verouderde prijzen worden niet stilzwijgend als actueel gebruikt.
8. Verkeerde valuta wordt niet stilzwijgend omgerekend.
9. Internationale referentie + FX is standaard **uitgeschakeld**.
10. Belastingen/heffingen worden niet automatisch verzonnen of toegepast.
11. Iedere berekende kostenregel houdt bron, datum, regio, valuta en FX-status vast.
12. Professionele review en productievrijgave blijven verplicht/vergrendeld.

## Prijsbronlocaties

Phoenix scant standaard:

- `inputs/market_prices/**/*.json`
- `data/market_prices/**/*.json`
- `configs/phoenix/market_price_ratebooks/**/*.json`

Autoritatieve HTTPS JSON-feeds kunnen later expliciet in
`market_price_source_registry_v1_0.json` worden geregistreerd. Phoenix levert
bewust geen verzonnen "live price API" mee.

## Ratebookcontract

Zie `configs/phoenix/market_price_ratebook_schema_v1_0.json`.

Minimaal vereist:
- country_code
- currency
- effective_date
- source_name
- prices[]
- per prijsregel: item_code, description, unit, unit_price

## PAT-gevolg

Wanneer de projectlocatie straks door Location Intelligence is opgelost:
- `CURRENCY_REQUIRED` wordt vervangen door een echte geografisch afgeleide valuta;
- kostenplanning mag pas verder wanneer actuele lokale/regionale marktprijsdata bestaat;
- zonder prijsbron stopt Phoenix gecontroleerd met `CURRENT_LOCAL_MARKET_PRICE_DATA_REQUIRED`.

Dat is bewust: Phoenix mag geen oude of niet-lokale prijzen presenteren alsof ze actueel en projectspecifiek zijn.

## FIXED R1 — regressiecontract gecorrigeerd

De eerste installatie stopte op één verouderde regressietest uit de vorige
Project Context-masterpack. Die test accepteerde een dummy `generic_ratebook.json`
zodra locatie en valuta bekend waren.

Dat is niet meer toegestaan. Local Cost Intelligence vereist nu expliciet:
**projectgeografie + lokale valuta + actuele lokale prijsbron + bron/datum/evidence**.

R1 wijzigt geen productiegedrag. De test bewijst nu:
- Amsterdam/Nederland -> EUR, maar zonder actuele lokale prijsbron: `BLOCKED_INPUT`;
- geldig actueel NL/EUR-prijsboek met bron en geldigheid: `PASSED`;
- stille FX blijft uit;
- automatische belastingfabricatie blijft uit;
- productievrijgave blijft `LOCKED`.
