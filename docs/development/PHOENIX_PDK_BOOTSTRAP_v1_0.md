# Phoenix Development Kit – Bootstrap v1.0

De Phoenix Development Kit is de vaste ontwikkelinterface voor
PROJECT-PHOENIX.

## Beschikbare commando's

### Repositorydiagnose

```powershell
python -m pdk doctor
```

Controleert:

- Python-versie;
- Git-repository;
- vereiste Phoenix Updater-modules;
- Python-imports;
- PDK-installatie.

### Structuursynchronisatie

```powershell
python -m pdk sync
```

Maakt ontbrekende runtime-, test- en documentatiemappen aan en voert daarna
de PDK Doctor uit.

### Testpipeline

```powershell
python -m pdk test
```

Voert de volledige unittest-discovery uit vanaf de repositoryroot.

## Herstel in Bootstrap v1.0

Deze bootstrap herstelt tevens de ontbrekende module:

```text
phoenix/updater/integrated_engine.py
```

Daardoor kan `phoenix.updater.api` opnieuw worden geïmporteerd en kan de
Phoenix Release Manager-test worden uitgevoerd.

## Vervolg

De volgende PDK-uitbreiding voegt permanente opdrachten toe voor:

```text
python -m pdk build
python -m pdk release
python -m pdk update
```