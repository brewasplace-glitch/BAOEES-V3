# Project Phoenix Core v30.0 â€” Phoenix Auto Release Pipeline

Definitieve standaardflow:

1. repository-preflight;
2. build;
3. syntax-tests;
4. unit-tests;
5. integratietests;
6. regressietests;
7. self-test;
8. runtime-evidence;
9. git diff --check;
10. controlled staging;
11. automatische commit;
12. automatische push;
13. finale controle op working tree clean.

Handmatige Git-finalisatie is vanaf v30.0 geen normaal releasepad meer.
