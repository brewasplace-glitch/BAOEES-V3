# Phoenix Multi-Material Design Engine — Wave 15.2 v1.0.0

## Purpose

Wave 15.2 generates deterministic, comparable structural alternatives across
concrete, steel, timber, masonry and other declared material families.

## Inputs

- design action;
- supplied system design resistance;
- system volume and element count;
- density;
- cost factor;
- embodied-carbon factor;
- durability and constructability scores.

## Outputs

Each feasible variant contains:

- material and system identifiers;
- utilization;
- mass;
- cost;
- embodied carbon;
- durability;
- constructability;
- Optimization Core metric mapping;
- SHA-256 evidence.

## Integration

- Wave 10: concrete design evidence;
- Wave 11: steel design evidence;
- Wave 12: timber and masonry design evidence;
- Wave 13: BIM/IFC;
- Wave 14: drawings;
- Wave 15.1: Pareto optimization and ranking;
- PVE/PRM/PRB/PUM: validation, recovery, packaging and update delivery.

## Limitations

Wave 15.2 uses supplied resistance values and factors. It does not itself
perform complete code-specific member sizing, connection design, fire design,
foundation redesign, approval or certification. Qualified engineering review
is mandatory.
