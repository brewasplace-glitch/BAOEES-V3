# Project Phoenix Core v33.1 — Unified Project Database Repair

## Hersteld

- Windows `WinError 32` bij het opruimen van tijdelijke SQLite-bestanden;
- expliciete sluiting van de verificatieverbinding in de rollback-test;
- geïsoleerde tijdelijke database voor iedere integratietest;
- herhaalbare integratietests zonder groeiende revisie- of historietellers;
- extra regressietest voor tweemaal achtereen uitvoeren;
- volledige automatische releasefinalisatie.

De functionele engineversie blijft v33.0. Deze reparatieversie is v33.1.
