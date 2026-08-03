# Phoenix Real-World Source Integration & Advanced Site Drawing Intelligence Masterpack v1.0

## Doel

Deze masterpack maakt de eerder gebouwde real-world acquisitielaag daadwerkelijk
bruikbaar voor een Suriname/Paramaribo PAT en verbetert PDF-situatieanalyse.

## A. Geconfigureerde Suriname-bronnen

Phoenix bevat een expliciet bronprofiel voor openbare bouwmarkt-/leverancierspagina's:
- Best Buy Suriname: cement, wapening/metaal en hout;
- N.V. VABI: bouwstenen;
- Horizon.sr: openbare bouwmateriaalprijzen;
- N.V. SUBEMA: lokale ready-mix concrete supplier capability;
- Hurricane Steel: lokale steel profiling/building-material capability;
- Government of Suriname: index Bouwwetten en regels.

Dit is **geen impliciete websearch**. Het zijn expliciet geconfigureerde HTTPS-bronnen.
Runtime failures blijven fail-safe en worden per provider geregistreerd.

## B. Market-price normalisatie

Openbare SRD-productprijzen worden naar Phoenix ratebooks genormaliseerd met:
- source URL;
- acquisitiedatum;
- SR/Paramaribo scope;
- SRD;
- productomschrijving;
- unit price;
- commerciële beschikbaarheidsstatus.

De bestaande Local Cost Intelligence freshness-/currency-gates blijven actief.

## C. Material availability vs engineering qualification

Vanaf deze versie zijn twee feiten strikt gescheiden:
1. **commercial local availability** — product kan lokaal worden gekocht/besteld;
2. **structural engineering qualification** — specifieke grade/strength class/material properties zijn technisch gevalideerd.

Cost Planning mag commerciële lokale beschikbaarheid gebruiken. Structural Solver
mag alleen engineering-gekwalificeerde producten gebruiken. Release Control blijft
geblokkeerd zolang constructieve technische productevidence ontbreekt.

## D. Advanced PDF Site Drawing Intelligence

Installer borgt `PyMuPDF` en `pypdf`. De parser kan:
- PDF-tekst extraheren;
- schaal `1:n` herkennen;
- vectorlijnen/paden uitlezen;
- gesloten rechthoekige parcel-candidates met expliciete schaal naar meters omzetten;
- expliciete perceelafmetingen herkennen;
- noordrichting alleen tonen als die expliciet is gevonden;
- straat-/weglabels als kandidaat-evidence registreren.

Zonder schaal/maatvoering wordt een willekeurige PDF-rechthoek niet als perceel
geaccepteerd. Kadastrale en planningsvalidatie blijven altijd apart.

## E. Structural load basis

De overheidspagina met Surinaamse bouwwetten wordt als regulatory reference snapshot
opgenomen, maar **niet** automatisch omgezet naar wind-/gebruiksbelasting of
combinatiefactoren. v8.2 blijft gecontroleerd blokkeren totdat een actuele,
professioneel genormaliseerde jurisdiction-matching `action_load_input` beschikbaar is.

## Veiligheid

- geen fictieve live bronnen;
- geen OCR-false-pass;
- geen kadastrale false-pass;
- geen normwaarde-fabricatie;
- geen stille materiaal-substitutie;
- production release blijft LOCKED.

## KULDIPSINGH R1 — Suriname source expansion

Kuldipsingh is added as an explicit Suriname real-world supplier source.

Configured evidence:
- Kuldipsingh building-material webshop as `material_supply`;
- the same public SRD product listings as `market_prices`;
- Kuldipsingh Readymix public concrete-mortar capability;
- Kuldipsingh concrete/prestressed-product public capability.

Kuldipsingh webshop prices are marked `taxes_included=false`, because the
public listings state prices excluding BTW.

The phrase `Alleen beschikbaar in de winkels` is normalized as commercial
`AVAILABLE_TO_ORDER` evidence for local-material availability. This does not
create an `engineering_material_id` and therefore cannot by itself qualify a
structural material for solver use.

Structural grade, strength class, section properties and project-specific
concrete mix/design remain separately gated.
