# PROJECT PHOENIX - R9.5.2.8 Remaining Evidence Gate Consolidation & Controlled R9.5 Requalification

## Doel

R9.5.2.8 consolideert de drie resterende R9.5 evidence/review gates:

- Package C - seismic scope & criteria;
- Package D - weak-storey screening professional review;
- Package E - independent alternate-load-path evidence.

Deze laag voegt geen nieuwe technische criteria of professionele beslissingen toe. Zij bepaalt uitsluitend of de bestaande C/D/E-resultaten expliciet voldoende zijn om een gecontroleerde nieuwe R9.5 requalification-pass te mogen starten.

## Fail-closed gate

Een requalification mag alleen worden aangeroepen wanneer alle drie package-resultaten expliciet aangeven dat ze eligible zijn voor latere R9.5-promotie. Ontbrekende, onvolledige of tegenstrijdige input houdt de status op `BLOCKED_REMAINING_EVIDENCE`.

Wanneer alle drie gates compleet zijn, wordt de bestaande R9.5.2.4 requalification-engine aangeroepen met een aangevulde R9.5.2 evidence-intake waarin C, D en E traceerbaar zijn opgenomen.

Het resultaat van de bestaande requalification-engine blijft volledig maatgevend. R9.5.2.8 verandert een uitgevoerde requalification niet automatisch in een succesvolle qualification.

## Harde veiligheidsgrenzen

R9.5.2.8:

- beslist seismic applicability niet automatisch;
- verzint geen numerieke criteria;
- accepteert de weak-storey screening proxy niet automatisch;
- genereert geen onafhankelijke alternate-path evidence;
- verzint geen reviewer of professional approval;
- claimt geen code compliance;
- claimt geen succesvolle R9.5 qualification;
- ontgrendelt Production niet;
- ontgrendelt FOR-CONSTRUCTION niet.

Production en FOR-CONSTRUCTION blijven `LOCKED`.

## Runtime-integratie

De structural chain krijgt een locals-only R9.5.2.8 hook direct na Package D. De hook ontvangt daarnaast uitsluitend een referentie naar de reeds bestaande R9.5.2.4 requalification-callable. Bestaande argumentlijsten van C, D of E worden niet gekloond.

De bestaande R9.5.2.2 path-literal contracttest blijft verplicht en moet exact blijven slagen.

## Installer-gates

De masterpack vereist:

1. branch `project-phoenix`;
2. baseline `9fda167dc85c7c9a05a1f1bcd3ff742df23b1fe7`;
3. clean en local/remote gesynchroniseerde worktree;
4. aanwezige Packages C, D en E;
5. aanwezige bestaande R9.5.2.4 requalification-callable in de structural chain;
6. Python syntaxvalidatie;
7. dedicated R9.5.2.8 tests;
8. R9.5.2.2 legacy path-literal compatibility test;
9. impact-tests voor C/D/E en R9.5.2.4;
10. volledige suite-aware regression inclusief root-smoke scripts;
11. cleanup van uitsluitend testgegenereerde `outputs/`;
12. `git diff --check`;
13. safety assertions;
14. secret scan;
15. fail-closed worktree scope;
16. automatische commit/push uitsluitend bij volledig groen;
17. rollback naar baseline bij de eerste fout.

PAT-001 wordt door deze framework-update niet opnieuw uitgevoerd.
