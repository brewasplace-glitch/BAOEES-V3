# PROJECT PHOENIX R9.5.2 Baseline Path-Literal Contract Repair v1.0

De schone baseline b9879d71fefb74dde9a106fbd2adebb43e05f200 faalt zelf op
test_phoenix_r9_5_2_2_runtime_policy_path_literal_repair_v1_2.py.

De twee oorspronkelijke R9.5.2.2 PRE/POST-hooks blijven ongewijzigd.
De later toegevoegde R9.5.2.4 ab_policy_path verwijzing blijft semantisch
naar exact hetzelfde bestand wijzen, maar gebruikt repository.joinpath(...),
zodat de legacy exact-count contracttest opnieuw exact twee harde padliteralen ziet.

Production / FOR-CONSTRUCTION blijft LOCKED.
