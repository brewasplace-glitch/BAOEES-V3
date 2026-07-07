param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "PROJECT PHOENIX - Repository Migration v1.0" -ForegroundColor Cyan
Write-Host ""

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path ".git")) {
    throw "Geen git repository gevonden. Voer dit script uit vanuit C:\BREWSTER-ENGINEERING-WIZARD."
}

if (-not (Test-Path "baoees")) {
    throw "Map 'baoees' niet gevonden. Dit lijkt niet de bestaande Brewster/BAOEES repository."
}

Write-Host "Stap 1 - Status vastleggen..." -ForegroundColor Yellow
git status --short | Set-Content -Encoding UTF8 "PROJECT_PHOENIX_pre_repo_migration_status.txt"

$changes = git status --short
if ($changes) {
    Write-Host "Bestaande wijzigingen gevonden. Ik maak eerst een stabilisatie-commit." -ForegroundColor Yellow
    git add -A
    git commit -m "chore: stabilize before project phoenix repository migration"
} else {
    Write-Host "Working tree schoon." -ForegroundColor Green
}

Write-Host "Stap 2 - Nieuwe Project Phoenix structuur aanmaken..." -ForegroundColor Yellow

$dirs = @(
    "apps",
    "apps/brewster_engineering_wizard",
    "apps/brewster_engineering_wizard/legacy_baoees",
    "apps/brewster_engineering_wizard/ui",
    "apps/brewster_engineering_wizard/config",
    "apps/brewster_engineering_wizard/docs",
    "phoenix_core",
    "phoenix_intelligence",
    "phoenix_intelligence/pkb",
    "phoenix_intelligence/bib",
    "phoenix_intelligence/knowledge_graph",
    "phoenix_intelligence/decision_log",
    "phoenix_intelligence/source_evidence",
    "suites",
    "suites/architectural",
    "suites/structural",
    "suites/geotechnical",
    "suites/infrastructure",
    "suites/permit",
    "suites/traffic_parking",
    "suites/mep",
    "suites/digital_twin",
    "docs/project_phoenix",
    "docs/project_phoenix/repository",
    "docs/project_phoenix/architecture"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

Write-Host "Stap 3 - App-shell en manifesten toevoegen..." -ForegroundColor Yellow

@'
# PROJECT PHOENIX

Project Phoenix is de centrale software-architectuur en ontwikkelbasis voor het volledige Brewster Engineering ecosysteem.

## Hoofdstructuur

- apps/brewster_engineering_wizard  
  De gebruikersapplicatie / UI-shell die de gebruiker ziet.

- phoenix_core  
  Centrale runtime, update-engine, registry, health monitor en platformbeheer.

- phoenix_intelligence  
  PKB + BIB + Knowledge Graph + STEE + decision log.

- suites  
  Engineering suites zoals Architectural, Structural, Geotechnical, Permit, Traffic & Parking, MEP en Digital Twin.

## Belangrijk

Vanaf deze migratie ontwikkelen we voortaan Project Phoenix als hoofdplatform.  
BREWSTER ENGINEERING WIZARD blijft de merknaam en gebruikersinterface.
'@ | Set-Content -Encoding UTF8 "PROJECT_PHOENIX_README.md"

@'
{
  "platform": "PROJECT PHOENIX",
  "repository_target_name": "PROJECT-PHOENIX",
  "application_brand": "BREWSTER ENGINEERING WIZARD",
  "app_path": "apps/brewster_engineering_wizard",
  "legacy_engine_path": "baoees",
  "migration_status": "phase_1_structure_created",
  "notes": [
    "The repository folder should be renamed manually from BREWSTER-ENGINEERING-WIZARD to PROJECT-PHOENIX after this commit is pushed.",
    "The existing baoees folder remains in place during the transition.",
    "Future releases will progressively move/alias functionality into apps, phoenix_core, phoenix_intelligence and suites."
  ]
}
'@ | Set-Content -Encoding UTF8 "project_phoenix_manifest.json"

@'
# Brewster Engineering Wizard App

Deze map wordt de nieuwe applicatielaag van Project Phoenix.

De gebruiker ziet:

BREWSTER ENGINEERING WIZARD

Maar de onderliggende software draait voortaan op:

PROJECT PHOENIX

## Rol van deze map

- UI
- dashboards
- projectstart
- gebruikersinstellingen
- koppeling naar Phoenix Core
- koppeling naar suites
- koppeling naar Phoenix Intelligence Layer
'@ | Set-Content -Encoding UTF8 "apps/brewster_engineering_wizard/README.md"

@'
{
  "app": "BREWSTER ENGINEERING WIZARD",
  "platform": "PROJECT PHOENIX",
  "role": "user_interface_shell",
  "status": "migration_started",
  "legacy_baoees_folder": "../../../baoees"
}
'@ | Set-Content -Encoding UTF8 "apps/brewster_engineering_wizard/app_manifest.json"

@'
# Repository Migration Decision

## Besluit

De repository wordt hernoemd van:

BREWSTER-ENGINEERING-WIZARD

naar:

PROJECT-PHOENIX

## Reden

Project Phoenix wordt het centrale platform.  
Brewster Engineering Wizard blijft bestaan als applicatie/gebruikersinterface binnen:

apps/brewster_engineering_wizard/

## Migratiestrategie

1. Nieuwe structuur toevoegen.
2. Oude BAOEES-map tijdelijk behouden.
3. Phoenix Core en PKB/BIB koppelen.
4. Functionaliteit geleidelijk verplaatsen of via adapters ontsluiten.
5. Hoofdmap lokaal hernoemen naar PROJECT-PHOENIX.
6. GitHub repository later eventueel ook hernoemen.
'@ | Set-Content -Encoding UTF8 "docs/project_phoenix/repository/REPOSITORY_RENAME_DECISION.md"

@'
# Project Phoenix Target Structure

```text
PROJECT-PHOENIX/
│
├── apps/
│   └── brewster_engineering_wizard/
│
├── phoenix_core/
│
├── phoenix_intelligence/
│   ├── pkb/
│   ├── bib/
│   ├── knowledge_graph/
│   ├── decision_log/
│   └── source_evidence/
│
├── suites/
│   ├── architectural/
│   ├── structural/
│   ├── geotechnical/
│   ├── infrastructure/
│   ├── permit/
│   ├── traffic_parking/
│   ├── mep/
│   └── digital_twin/
│
├── baoees/
│   └── legacy transition layer
│
├── docs/
├── configs/
├── outputs/
└── tests/
```
'@ | Set-Content -Encoding UTF8 "docs/project_phoenix/architecture/TARGET_REPOSITORY_STRUCTURE.md"

Write-Host "Stap 4 - Migratie commit maken..." -ForegroundColor Yellow
git add PROJECT_PHOENIX_README.md project_phoenix_manifest.json apps phoenix_core phoenix_intelligence suites docs/project_phoenix PROJECT_PHOENIX_pre_repo_migration_status.txt
git commit -m "chore: start migration to project phoenix repository structure"

Write-Host ""
Write-Host "Stap 5 - Status tonen..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "KLAAR: Project Phoenix repository-structuur is voorbereid." -ForegroundColor Green
Write-Host "Voer nu uit: git push" -ForegroundColor Green
Write-Host ""
Write-Host "Daarna mag je Windows-map hernoemen van:" -ForegroundColor Cyan
Write-Host "C:\BREWSTER-ENGINEERING-WIZARD" -ForegroundColor Cyan
Write-Host "naar:" -ForegroundColor Cyan
Write-Host "C:\PROJECT-PHOENIX" -ForegroundColor Cyan