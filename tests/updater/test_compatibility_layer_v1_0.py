import unittest

from phoenix.updater.api import PackageBuilder, ReleasePackageBuilder
from phoenix.updater.package_builder import PackageBuilder as LegacyPackageBuilder
from phoenix.updater.release_package_builder import (
    ReleasePackageBuilder as DirectReleasePackageBuilder,
)


class CompatibilityLayerTests(unittest.TestCase):
    def test_legacy_builder_remains_public(self) -> None:
        self.assertIs(PackageBuilder, LegacyPackageBuilder)

    def test_release_builder_is_separate(self) -> None:
        self.assertIs(ReleasePackageBuilder, DirectReleasePackageBuilder)
        self.assertIsNot(PackageBuilder, ReleasePackageBuilder)


if __name__ == "__main__":
    unittest.main()