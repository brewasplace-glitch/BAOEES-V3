from baoees.phoenix_core.update_engine.update_engine import PhoenixUpdateEngine


def main():
    result = PhoenixUpdateEngine().run_bootstrap()
    print("PROJECT PHOENIX CORE")
    print("Version: 1.0.0")
    print("Health OK:", result["health"]["overall_ok"])


if __name__ == "__main__":
    main()
