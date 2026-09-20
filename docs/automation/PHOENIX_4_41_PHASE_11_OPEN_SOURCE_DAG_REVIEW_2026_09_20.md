# PROJECT PHOENIX 4.41 — Phase 11 Open-Source Review

Date: 2026-09-20

Primary: Python `graphlib.TopologicalSorter` (PSF-2.0)
Documentation: https://docs.python.org/3/library/graphlib.html

Bounded parallel executor: Python `concurrent.futures.ThreadPoolExecutor`
Documentation: https://docs.python.org/3/library/concurrent.futures.html

Inspection fallback: NetworkX (BSD-3-Clause)
Documentation: https://networkx.org/documentation/stable/reference/algorithms/dag.html

Airflow, Dagster and Prefect were not selected because Phase 11 needs a small,
embedded and dependency-free runtime rather than a separately deployed control
plane. Phoenix builds only its policy, evidence and agent contracts around the
accepted standard-library primitives.
