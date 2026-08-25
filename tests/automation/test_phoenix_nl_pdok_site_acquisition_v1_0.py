import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from phoenix.autonomy.nl_pdok_site_acquisition_v1_0 import (
    acquire_nl_pdok_site_evidence,
)


def square(x1, y1, x2, y2):
    return {
        "type": "Polygon",
        "coordinates": [[
            [x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]
        ]],
    }


class NlPdokSiteAcquisitionTests(unittest.TestCase):
    def context(self, country="NL"):
        return {
            "facts": {
                "country_code": country,
                "project_location": "Bikkersweg 88, Bunschoten",
            }
        }

    def base(self):
        return {
            "schema_version": "phoenix.site-context/1.0",
            "status": "SCHEMATIC_ASSUMPTION",
            "plot": {
                "width_m": 6.0,
                "depth_m": 10.0,
                "source": "AUTO_SCHEMATIC_DESIGN_CANVAS",
                "legal_boundary": False,
            },
            "cadastral_validation": False,
            "planning_validation": False,
            "production_release": "LOCKED",
        }

    def fetcher(self, *, parcel_count=1, boundary=False):
        lon, lat = 5.35979, 52.245309
        location = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"weergavenaam": "Bikkersweg 88, Bunschoten"},
            }],
        }
        if boundary:
            parcel_geom = square(lon, lat - 0.0001, lon + 0.0002, lat + 0.0001)
        else:
            parcel_geom = square(lon - 0.0001, lat - 0.0001, lon + 0.0001, lat + 0.0001)

        parcels = []
        for idx in range(parcel_count):
            parcels.append({
                "type": "Feature",
                "geometry": parcel_geom,
                "properties": {
                    "kadastrale_gemeente_waarde": "Bunschoten",
                    "kadastrale_gemeente_code": "177",
                    "sectie": "M",
                    "perceelnummer": 419 + idx,
                    "kadastrale_grootte_waarde": 260,
                },
            })

        bag = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": square(
                    lon - 0.00002, lat - 0.00002, lon + 0.00002, lat + 0.00002
                ),
                "properties": {
                    "identificatie": "0313100000187651",
                    "status": "Pand in gebruik",
                },
            }],
        }

        def fetch(url):
            if "location-api" in url or "locatieserver" in url:
                return location
            if "brk-kadastrale-kaart" in url:
                return {"type": "FeatureCollection", "features": parcels}
            if "/bag/" in url:
                return bag
            raise AssertionError(url)
        return fetch

    def test_unique_containing_parcel_is_applied_but_not_legalized(self):
        with tempfile.TemporaryDirectory() as td:
            result = acquire_nl_pdok_site_evidence(
                project_id="P",
                project_context=self.context(),
                base_site_context=self.base(),
                existing_evidence_register={"evidence": [], "warnings": []},
                output_dir=Path(td),
                fetch_json=self.fetcher(),
            )
            self.assertTrue(result.applied)
            self.assertEqual(result.status, "PDOK_BRK_CONTAINING_PARCEL_CONFIRMED")
            self.assertEqual(result.site_context["status"], "PDOK_BRK_SITE_EVIDENCE")
            self.assertFalse(result.site_context["plot"]["legal_boundary"])
            self.assertFalse(result.site_context["cadastral_validation"])
            self.assertFalse(result.evidence_register["automatic_legal_boundary_claim"])
            self.assertEqual(result.evidence_register["selected_parcel"]["sectie"], "M")
            self.assertEqual(result.evidence_register["selected_parcel"]["perceelnummer"], 419)
            self.assertTrue(
                any(p.name == "pdok_selected_parcel.geojson" for p in result.output_files)
            )

    def test_multiple_containing_parcels_are_not_auto_selected(self):
        with tempfile.TemporaryDirectory() as td:
            result = acquire_nl_pdok_site_evidence(
                project_id="P",
                project_context=self.context(),
                base_site_context=self.base(),
                existing_evidence_register={"evidence": [], "warnings": []},
                output_dir=Path(td),
                fetch_json=self.fetcher(parcel_count=2),
            )
            self.assertFalse(result.applied)
            self.assertEqual(result.status, "AMBIGUOUS_OR_NO_CONTAINING_PARCEL")
            self.assertEqual(result.site_context["status"], "SCHEMATIC_ASSUMPTION")

    def test_boundary_hit_is_not_auto_selected(self):
        with tempfile.TemporaryDirectory() as td:
            result = acquire_nl_pdok_site_evidence(
                project_id="P",
                project_context=self.context(),
                base_site_context=self.base(),
                existing_evidence_register={"evidence": [], "warnings": []},
                output_dir=Path(td),
                fetch_json=self.fetcher(boundary=True),
            )
            self.assertFalse(result.applied)
            self.assertEqual(result.status, "AMBIGUOUS_OR_NO_CONTAINING_PARCEL")

    def test_non_nl_project_never_calls_pdok(self):
        with tempfile.TemporaryDirectory() as td:
            fetch = Mock(side_effect=AssertionError("network must not be called"))
            result = acquire_nl_pdok_site_evidence(
                project_id="P",
                project_context=self.context("SR"),
                base_site_context=self.base(),
                existing_evidence_register={},
                output_dir=Path(td),
                fetch_json=fetch,
            )
            self.assertFalse(result.applied)
            self.assertEqual(result.status, "NOT_APPLICABLE_COUNTRY")
            fetch.assert_not_called()

    def test_existing_real_site_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            fetch = Mock(side_effect=AssertionError("network must not be called"))
            base = self.base()
            base["status"] = "SITE_DRAWING_EVIDENCE"
            result = acquire_nl_pdok_site_evidence(
                project_id="P",
                project_context=self.context(),
                base_site_context=base,
                existing_evidence_register={},
                output_dir=Path(td),
                fetch_json=fetch,
            )
            self.assertFalse(result.applied)
            self.assertEqual(result.status, "EXISTING_SITE_EVIDENCE_PRESERVED")
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
