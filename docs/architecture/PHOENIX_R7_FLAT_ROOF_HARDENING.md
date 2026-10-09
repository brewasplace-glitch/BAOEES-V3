# PHOENIX R7 — Flat Roof Hardening

Plutostraat explicitly requires a flat roof. R7 therefore preserves architectural
pitch 0.0 instead of forcing a pitched tropical roof form.

This hardening:
- keeps architectural pitch at 0.0;
- makes `roof_type=FLAT` and `architectural_form=FLAT` explicit;
- treats drainage fall as a separate unresolved design input rather than silently
  converting the architectural roof to a pitched roof;
- changes IFC semantics to `IfcRoof.PredefinedType=FLAT_ROOF`;
- changes the IFC roof name to `Flat Roof`;
- adds a true flat-roof Blender mesh path;
- prevents strategy branches from forcing 12 or 22 degree roof pitches when the
  canonical architectural pitch is zero.

No drainage slope, parapet geometry, outlet count, waterproofing system or
structural truss sizing is invented here. Those remain later technical design
inputs. Release remains concept-only / not for construction.
