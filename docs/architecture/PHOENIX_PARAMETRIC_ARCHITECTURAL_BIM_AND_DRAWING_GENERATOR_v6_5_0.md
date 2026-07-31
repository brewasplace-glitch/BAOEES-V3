# Phoenix Parametric Architectural BIM and Drawing Generator v6.5.0

## Strategic change

v6.5.0 removes the Moskee Bunschoten pilot from the default architectural
execution path. The generator is now project-independent and starts from a
generic architectural project program.

## Generated content

The generator creates:

- a validated architectural program;
- deterministic space layouts per storey;
- a central architectural Digital Twin;
- a real FreeCAD native model and STEP export;
- a real IFC4 model containing project, building, storeys and spaces;
- floor plans;
- four elevations;
- a section;
- room, opening, material and quantity schedules;
- a drawing index;
- an architectural quality report;
- a SHA-256 artifact manifest;
- permit-ready and execution-ready release gates.

## Release safety

The software may generate a complete architectural package structure, but it
must not mark a project permit-ready or execution-ready without verified site
data, an applicable jurisdiction profile and explicit professional approval.

Future versions can deepen wall, opening, stair, roof, fire-safety, building
physics, accessibility and detailing logic without returning to a pilot-bound
architecture.
