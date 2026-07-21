# Phoenix Autonomous Project Delivery Master Specification v1.0

## North-star command

> Ontwerp een appartementencomplex op deze locatie.

Phoenix must generate exactly ten materially different concept designs, show
them one by one, and support automatic selection, user selection or an
externally supplied design.

For the selected design Phoenix coordinates:

- location and GIS analysis;
- soil and geotechnical analysis;
- foundation selection, design and calculation;
- structural steel and concrete design;
- construction and specification drawings;
- sewerage, climate, electrical and water-supply design;
- traffic and parking analysis;
- fire safety and sustainability;
- BIM and digital-twin coordination;
- total cost calculation;
- permit generation and compliance control;
- construction planning;
- complete dossier assembly.

The final dossier includes the structural report, geotechnical report, permit
dossiers, specification drawings, bill of quantities, cost estimate, schedule,
source register, assumptions log and unresolved-blocker register.

Existing engines are registered and reused; they are not duplicated. Every new
engine must expose inputs, outputs, SI units, evidence, assumptions,
dependencies, quality gates and failure states.

Phoenix stops at the first failed quality gate and may only publish a complete
dossier when cross-discipline consistency and mandatory evidence checks pass.
