# PHOENIX AUTO SYNC — NL PDOK Site Acquisition Bridge v1.0

Real-project evidence for Moskee Bunschoten proved:
- PDOK Location API resolved Bikkersweg 88, Bunschoten;
- BRK Kadastrale Kaart returned local parcel features;
- robust CRS84 point-in-polygon diagnostics found exactly one containing parcel:
  Bunschoten, section M, parcel 419, registered area attribute 260 m2;
- BAG returned exactly one containing building for the address point.

Phoenix now extends the existing site/parcel evidence path with an NL-only PDOK bridge.
It auto-selects a parcel only on unique containment and keeps the geometry explicitly
indicative: no legal-boundary claim, no cadastral validation, no planning validation,
professional review required, production/FOR CONSTRUCTION locked.
