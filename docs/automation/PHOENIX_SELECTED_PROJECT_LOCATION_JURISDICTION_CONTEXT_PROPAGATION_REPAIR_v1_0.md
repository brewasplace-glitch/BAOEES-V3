# Phoenix Selected-Project Location/Jurisdiction Context Propagation Repair v1.0

## Proven blocker

`PROJECT_LOCATION_JURISDICTION_REQUIRED`

The real Moskee Bunschoten project binding already contains the explicit project location
`Bikkersweg 88, Bunschoten` and country `Nederland`, but Generic Session permit routing did
not consume selected-project facts.

## Repair

Before Location Intelligence runs, Phoenix now reads explicit facts from the selected
project JSON and merges only missing facts into the central project context.

This is a context/routing repair, not a geocoder and not a legal rules engine.

Known explicit country names used by Phoenix projects can be normalized to ISO-2. Unknown
country names are not guessed.

Permit routing still produces candidate context only. Current permit/BOPA/AERIUS rules
still require source evidence. Automatic legal conclusion and professional approval remain
disabled; production/FOR CONSTRUCTION release remains locked.
