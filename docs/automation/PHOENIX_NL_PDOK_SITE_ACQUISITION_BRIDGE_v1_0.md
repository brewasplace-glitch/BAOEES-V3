# Phoenix NL PDOK Site Acquisition Bridge v1.0

## Purpose

Extend the existing Phoenix site/parcel intelligence path for Netherlands projects that
have an explicit location but no machine-readable site geometry.

## Open-source / open-data-first architecture

Primary:
1. PDOK Location API for address geocoding.
2. BRK Kadastrale Kaart OGC API for indicative parcel geometry.

Fallback / corroborating context:
1. PDOK Locatieserver when the primary geocoder does not yield a usable point.
2. BAG OGC API for address-point building containment context.

No new Python dependency is introduced; the implementation uses the Python standard
library.

## Safety contract

The BRK Kadastrale Kaart geometry is used only as Level-A candidate site evidence.
Phoenix does not claim a legal cadastral boundary and does not infer legal dimensions.

Automatic selection is allowed only when:
- country is explicitly NL;
- project location is explicit;
- existing site context is still schematic;
- exactly one BRK parcel contains the geocoded address point;
- the point is not treated as a parcel-boundary hit.

Otherwise the existing `SITE_FACTS_REQUIRED_FOR_SITUATION_PLAN` fail-closed behavior is
preserved.

`cadastral_validation=false`, `planning_validation=false`, professional review is
required, production release remains LOCKED and FOR CONSTRUCTION is not enabled.
