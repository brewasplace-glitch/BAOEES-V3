# PROJECT PHOENIX — Route-Aware Schema + v8.0 Compatibility Bridge Repair v1.0

## Bound baseline
`project-phoenix` @ `debf369f1ad6b0d66eae048c801eb9e7a0cb17cd`

## Proven blocker chain
Diagnostics v3.0–v3.4 proved:

- the Start-v3 A–E nonresidential route and the Generic Session Orchestrator are both valid;
- structural capability selection is valid;
- the bridge reaches the Generic Session Orchestrator;
- the primary published architecture model is not a safe structural source because its
  `levels` field is scalar after A–E publication;
- the recommended A–E canonical model still preserves the real `levels`, `walls`,
  `spaces`, and `openings` relationships;
- a lossless `levels -> storeys` compatibility view satisfies the Generic architecture
  and detailed-elements gates;
- v8.0 then requires compatibility field names (`element_id`, `storey_id`) and geometric
  values (`length_m`, rectangular space bbox);
- the full lossless normalization yields a genuine v8.0
  `structural_candidate_model.json`, with positive wall lengths and no fabricated
  engineering facts.

## Repair
This repair is bridge-local. It does not redefine the authoritative architectural model.

The structural bridge now:
1. reads `recommended_variant_id` from the nonresidential delivery manifest;
2. selects that recommended variant's preserved canonical architectural model;
3. creates an isolated Generic Session workspace below the architectural job;
4. creates a temporary official-start upload batch containing a compatibility view;
5. preserves all original canonical arrays and adds only lossless aliases/derivations;
6. executes the existing Generic Session Orchestrator;
7. publishes only `structural_engineering` results back into the primary project runtime
   when genuine structural artifacts exist;
8. never overwrites the primary A–E architecture or authoritative IFC.

## Lossless mappings
- storey.storey_id = storey.id
- wall.element_id = wall.id
- wall.storey_id = wall.level_id
- space.element_id = space.id
- space.space_id = space.id
- space.storey_id = space.level_id
- wall.length_m = Euclidean distance between existing wall start/end coordinates
- wall.category = existing `external` boolean
- rectangular space x/y/width/depth = exact bbox of existing axis-aligned polygon

Non-rectangular space polygons stop fail-safe instead of inventing geometry.

## Governance
Production release remains LOCKED. FOR CONSTRUCTION remains LOCKED. Professional
structural review remains required. No automatic structural approval is introduced.
