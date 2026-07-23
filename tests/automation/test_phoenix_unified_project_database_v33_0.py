from pathlib import Path
import tempfile
import unittest

from phoenix.database import ProjectDatabase


class ProjectDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = ProjectDatabase("TEST-001", Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_and_read_object(self) -> None:
        obj = self.db.create_object("building", "Main Building")
        loaded = self.db.objects.require(obj.object_id)
        self.assertEqual(loaded.name, "Main Building")

    def test_relationship_requires_existing_objects(self) -> None:
        source = self.db.create_object("building", "A")
        with self.assertRaises(KeyError):
            self.db.relate(source.object_id, "contains", "missing")

    def test_delete_with_relationship_is_blocked(self) -> None:
        building = self.db.create_object("building", "A")
        storey = self.db.create_object("storey", "B")
        self.db.relate(building.object_id, "contains", storey.object_id)
        with self.assertRaises(ValueError):
            self.db.delete_object(building.object_id)

    def test_update_increments_version(self) -> None:
        obj = self.db.create_object("beam", "B1")
        updated = self.db.update_object(obj.object_id, name="B2")
        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.name, "B2")

    def test_save_and_load(self) -> None:
        obj = self.db.create_object("space", "Room 1")
        checksum = self.db.save()
        self.assertEqual(len(checksum), 64)
        other = ProjectDatabase("TEST-001", Path(self.tmp.name))
        other.load()
        self.assertEqual(other.objects.require(obj.object_id).name, "Room 1")

    def test_snapshot_restore(self) -> None:
        obj = self.db.create_object("beam", "B1")
        record = self.db.create_snapshot()
        self.db.update_object(obj.object_id, name="Changed")
        self.db.restore_snapshot(record)
        self.assertEqual(self.db.objects.require(obj.object_id).name, "B1")

    def test_snapshot_compare(self) -> None:
        left = self.db.to_dict()
        self.db.create_object("column", "C1")
        right = self.db.to_dict()
        result = self.db.snapshots.compare(left, right)
        self.assertEqual(result["object_count_delta"], 1)


if __name__ == "__main__":
    unittest.main()
