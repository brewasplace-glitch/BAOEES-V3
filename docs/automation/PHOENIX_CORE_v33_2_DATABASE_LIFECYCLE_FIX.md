# Project Phoenix Core v33.2 — Database Engine Lifecycle Fix

De SQLite connection-contextmanager commit of rollbackt, maar sluit een connection niet automatisch. Daardoor bleven Windows-databasebestanden vergrendeld.

Hersteld:

- centrale `connection()`-contextmanager met expliciete `close()`;
- transactionele context met rollback, commit en deterministische afsluiting;
- engine-lifecycle via `close()`, `__enter__` en `__exit__`;
- alle queries en schema-initialisatie via dezelfde veilige connection-factory;
- geïsoleerde integratiedatabases;
- daadwerkelijke rename- en delete-controles op vrijgegeven bestanden;
- herhaalde integratie- en regressietests.

De functionele databaseversie blijft v33.0. De lifecycle-fix is v33.2.
