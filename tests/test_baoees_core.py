from baoees.core.main import BAOEESCore


def test_baoees_core_start_projectanalyse():
    core = BAOEESCore()
    core.start_projectanalyse()
    assert True
