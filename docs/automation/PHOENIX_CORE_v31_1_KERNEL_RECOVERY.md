# Project Phoenix Core v31.1 — Phoenix Kernel Recovery

## Herstel

v31.1 verwijdert de importgevoelige `@dataclass`-constructie uit de
kernel-eventstructuur en vervangt deze door een gewone, robuuste Pythonklasse.

## Functies

- centrale Event Bus;
- centrale Service Bus;
- Engine Lifecycle Manager;
- Plugin Loader;
- uniforme kernel-interface;
- plugin-discovery;
- kernel bootstrap;
- integratietest;
- automatische commit en push;
- finale controle op `working tree clean`.

```powershell
.\runners\PROJECT_PHOENIX_v31_1_kernel.ps1 -Mode summary
```
