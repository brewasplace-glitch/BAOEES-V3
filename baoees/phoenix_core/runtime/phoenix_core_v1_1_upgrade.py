from baoees.phoenix_core.dashboard.dashboard_builder import PhoenixDashboardBuilder
from baoees.phoenix_core.package_manager.package_manager import PhoenixPackageManager
from baoees.phoenix_core.versioning.version_manager import PhoenixVersionManager
from baoees.phoenix_core.plugin_loader.plugin_loader import PhoenixPluginLoader


def main():
    version = PhoenixVersionManager().set_version("1.1.0")
    dashboard = PhoenixDashboardBuilder().build()
    package = PhoenixPackageManager().create_package_manifest(
        "phoenix_core",
        "1.1.0",
        files=[
            "dashboard_builder.py",
            "package_manager.py",
            "version_manager.py",
            "plugin_loader.py"
        ]
    )
    plugins = PhoenixPluginLoader().list_plugins()

    print("Phoenix Core v1.1 Manager Upgrade voltooid.")
    print("Version:", version["version"])
    print("Dashboard cards:", len(dashboard["cards"]))
    print("Plugins:", len(plugins.get("plugins", [])))
    print("Package:", package["package_name"], package["version"])


if __name__ == "__main__":
    main()
