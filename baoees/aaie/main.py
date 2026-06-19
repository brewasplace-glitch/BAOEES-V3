class AAIE:
    def infer_missing_parameters(self, project=None):
        return {
            "status": "COMPLEET",
            "message": "Ontbrekende gegevens aangevuld met aannames.",
            "parameter_status": "AANNAME"
        }

    def generate_groundwater_level(self):
        return {
            "groundwater_level": -0.50,
            "unit": "m t.o.v. P",
            "status": "AANNAME"
        }

    def compare_foundations(self):
        return {
            "foundation_types": ["strokenfundering", "paalfundering"],
            "status": "TE_VERGELIJKEN"
        }
