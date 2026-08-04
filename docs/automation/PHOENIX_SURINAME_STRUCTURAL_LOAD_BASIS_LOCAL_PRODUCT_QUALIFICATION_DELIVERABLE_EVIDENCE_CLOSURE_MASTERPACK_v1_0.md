# Phoenix Suriname Structural Load Basis, Local Product Qualification & Deliverable Evidence Closure Masterpack v1.0

## Doel

Deze masterpack sluit de in de real-project PAT aangetoonde integratiegaten tussen:

1. Suriname structurele kennis en v8.2 Structural Action & Load Model;
2. real-world leveranciersbronnen en Local Material / Product & Supply Intelligence;
3. daadwerkelijk gegenereerde projectartifacts en de Suriname Minimum Deliverable Baseline;
4. capability-status en de gewenste-outputstatus in de autonome result index.

## Harde veiligheidsregels

- De Suriname load-basis is een user-approved interim engineering policy en wordt niet als geverifieerd Surinaams recht gepresenteerd.
- De referentiewaarden 1.75 kN/m2 woonvloer en 0.45 kN/m2 wind zijn uitsluitend opgenomen in het laagbouw-woningprofiel en zijn terug te voeren op de door de gebruiker aangeleverde Suriname practice-evidence. Zij worden niet als universele projectdefaults aangemerkt.
- Sneeuwbelasting is uitgesloten conform de vastgelegde interim policy, tenzij projectspecifieke evidence anders vereist.
- Lokale beschikbaarheid wordt nooit verzonnen. Alleen expliciet bronmateriaal met beschikbaarheidsstatus telt.
- Een engineering_material_id wordt alleen afgeleid uit een expliciete product-/sterkteklasse of technische producteigenschap.
- Capability PASSED betekent niet automatisch Desired Output PASSED. Een echt, niet-leeg artifact en passende evidence-gate zijn vereist.
- Professionele goedkeuring blijft menselijk. Production release blijft LOCKED.

## Nieuwe componenten

- `phoenix/autonomy/suriname_structural_load_basis.py`
- `phoenix/autonomy/local_product_qualification.py`
- `phoenix/autonomy/desired_output_evidence.py`
- `phoenix/autonomy/deliverable_evidence_resolver.py`

## Integratie

### Architecture
Na real-world acquisition en project-context generatie maakt Phoenix een projectspecifieke Local Product Qualification Overlay. Deze overlay normaliseert uitsluitend reeds verworven supplier evidence naar het bestaande material-supply contract.

### Structural
Voor een Suriname laagbouw-woning wordt voor v8.2 een project-runtime structural_action_load source gemaakt met traceability, een expliciete interim-policy status en een blijvende professional-review lock.

### Minimum Deliverable Closure
Voor de baseline-evaluatie genereert de Deliverable Evidence Resolver automatisch `orchestration/minimum_deliverable_manifest.json`. Bestaande plattegronden, gevels, doorsneden en situatietekening worden hierdoor niet langer opnieuw als 'niet expliciet gevalideerd' geblokkeerd wanneer hun geregistreerde artifacts werkelijk bestaan.

### Desired Output False-Pass Protection
De Session-Driven Orchestrator controleert voortaan per gewenste output een concreet artifact. Voorbeeld: Digital Twin JSON kan de Digital Twin-output bewijzen, maar een 3D Viewer vereist een echte `.html/.gltf/.glb` viewer en automatische video vereist een echte video-file.

## Verwachte volgende PAT

Deze masterpack hoort de huidige v8.2 load-basis blocker te sluiten voor de gedefinieerde Suriname laagbouw-woningprofile en de lokale material gate aantoonbaar beter te voeden. De structurele keten mag daarna terecht op een latere engineering-input gate blokkeren, bijvoorbeeld solver-basis of solverresultaten; die worden in deze masterpack niet verzonnen.
