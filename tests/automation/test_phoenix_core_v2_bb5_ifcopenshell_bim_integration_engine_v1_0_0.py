import json
import tempfile
import unittest
from pathlib import Path

from phoenix.osif.adapters import (
    AdapterContext,
    AdapterExecutionRequest,
    IfcOpenShellAdapter,
    IfcOpenShellIntegrationError,
)


class FakeEntity:
    def __init__(self, entity_id, entity_type, **attributes):
        self._id = entity_id
        self._type = entity_type
        for key, value in attributes.items():
            setattr(self, key, value)

    def id(self):
        return self._id

    def is_a(self):
        return self._type

    def get_info(self, recursive=False):
        return {
            "id": self._id,
            "type": self._type,
            "Name": getattr(self, "Name", None),
        }


class FakeModel:
    schema = "IFC4"

    def __init__(self):
        self.entities = [
            FakeEntity(1, "IfcProject", GlobalId="P1", Name="Project"),
            FakeEntity(2, "IfcSite", GlobalId="S1", Name="Site"),
            FakeEntity(3, "IfcBuilding", GlobalId="B1", Name="Building"),
            FakeEntity(
                4,
                "IfcBuildingStorey",
                GlobalId="L1",
                Name="Ground",
                Elevation=0.0,
            ),
            FakeEntity(5, "IfcSpace", GlobalId="R1", Name="Room"),
            FakeEntity(6, "IfcWall", GlobalId="W1", Name="Wall"),
        ]

    def by_type(self, entity_type):
        if entity_type == "IfcProduct":
            return [
                item
                for item in self.entities
                if item.is_a() in {"IfcWall", "IfcSpace"}
            ]
        if entity_type == "IfcObject":
            return [
                item
                for item in self.entities
                if item.is_a() in {"IfcWall", "IfcSpace"}
            ]
        return [
            item
            for item in self.entities
            if item.is_a() == entity_type
        ]

    def create_entity(self, entity_type, **attributes):
        item = FakeEntity(
            len(self.entities) + 1,
            entity_type,
            **attributes,
        )
        self.entities.append(item)
        return item

    def write(self, destination):
        Path(destination).write_text(
            "ISO-10303-21;\nEND-ISO-10303-21;\n",
            encoding="utf-8",
        )

    def __iter__(self):
        return iter(self.entities)


class FakeIfcModule:
    version = "0.8.fake"

    def __init__(self):
        self.model = FakeModel()

    def open(self, source):
        return self.model

    def file(self, schema="IFC4"):
        self.model = FakeModel()
        self.model.schema = schema
        return self.model


class FakeElementUtil:
    @staticmethod
    def get_psets(entity):
        return {"Pset_Test": {"Reference": entity.id()}}


class FakeLogger:
    statements = []


class FakeValidate:
    @staticmethod
    def json_logger():
        return FakeLogger()

    @staticmethod
    def validate(model, logger):
        return None


class Loader:
    def __init__(self):
        self.ifc = FakeIfcModule()

    def __call__(self, name):
        if name == "ifcopenshell":
            return self.ifc
        if name == "ifcopenshell.util.element":
            return FakeElementUtil
        if name == "ifcopenshell.validate":
            return FakeValidate
        raise ImportError(name)


class BB5IfcOpenShellTests(unittest.TestCase):
    def source(self, folder):
        path = Path(folder) / "model.ifc"
        path.write_text(
            "ISO-10303-21;\nEND-ISO-10303-21;\n",
            encoding="utf-8",
        )
        return path

    def adapter(self):
        return IfcOpenShellAdapter(module_loader=Loader())

    def test_health_check(self):
        health = self.adapter().health_check()
        self.assertEqual(health.status, "available")
        self.assertEqual(health.details["version"], "0.8.fake")

    def test_descriptor_operational(self):
        descriptor = self.adapter().descriptor()
        self.assertEqual(
            descriptor.metadata["bb5_status"],
            "operational",
        )
        self.assertTrue(
            any(
                item.capability_id == "ifc.validate"
                for item in descriptor.capabilities
            )
        )

    def test_read_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = self.adapter()
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "read-1",
                    "PHX",
                    "ifc.read",
                    {"source_file": str(self.source(folder))},
                    folder,
                )
            )
            self.assertEqual(
                result.outputs["data"]["building_count"],
                1,
            )

    def test_query(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = self.adapter()
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "query-1",
                    "PHX",
                    "ifc.query",
                    {
                        "source_file": str(self.source(folder)),
                        "entity_type": "IfcWall",
                    },
                    folder,
                )
            )
            self.assertEqual(result.outputs["data"]["count"], 1)

    def test_property_sets(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = self.adapter()
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "pset-1",
                    "PHX",
                    "ifc.pset.read",
                    {"source_file": str(self.source(folder))},
                    folder,
                )
            )
            self.assertEqual(
                len(result.outputs["data"]["products"]),
                2,
            )

    def test_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = self.adapter()
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "validate-1",
                    "PHX",
                    "ifc.validate",
                    {"source_file": str(self.source(folder))},
                    folder,
                )
            )
            self.assertTrue(result.outputs["data"]["is_valid"])

    def test_digital_twin_export(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "digital_twin.json"
            adapter = self.adapter()
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "dt-1",
                    "PHX",
                    "ifc.digital_twin.export",
                    {
                        "source_file": str(self.source(folder)),
                        "destination_file": str(destination),
                    },
                    folder,
                )
            )
            self.assertTrue(destination.is_file())
            self.assertTrue(result.metadata["digital_twin_ready"])
            self.assertEqual(len(result.evidence_sha256), 64)

    def test_write_ifc(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "generated.ifc"
            adapter = self.adapter()
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "write-1",
                    "PHX",
                    "ifc.write",
                    {
                        "destination_file": str(destination),
                        "schema": "IFC4",
                        "entities": [
                            {
                                "type": "IfcProject",
                                "attributes": {"Name": "Phoenix"},
                            }
                        ],
                    },
                    folder,
                )
            )
            self.assertTrue(destination.is_file())
            self.assertEqual(result.status, "completed")

    def test_missing_query_type_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = self.adapter()
            adapter.initialize(AdapterContext("PHX", folder))
            with self.assertRaisesRegex(
                IfcOpenShellIntegrationError,
                "requires entity_type",
            ):
                adapter.execute(
                    AdapterExecutionRequest(
                        "bad-query",
                        "PHX",
                        "ifc.query",
                        {"source_file": str(self.source(folder))},
                        folder,
                    )
                )


if __name__ == "__main__":
    unittest.main()
