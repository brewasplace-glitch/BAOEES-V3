# Project Phoenix — Model-Driven Calculation Dossier

**CONCEPT CALCULATIONS - NOT FOR SUBMISSION OR EXECUTION**

Model: `HBM-GEO-2026-001`
Model fingerprint: `61c1c56f500192557d603552561dd408cfed09fe704247b26f18343d24f1af0a`

Calculations: 32
QA: 18/18

## Area Volume

### CAL-A01 — Extension floor area
- Formula/methode: `width * length`
- Resultaat: **70.0 m2**
- Model: BLD-EXTENSION
- Tekeningen: A-101, A-102
- Rapporten: R-101
- REQ: REQ-102
- Status: SIMULATION_ONLY

### CAL-A02 — Extension gross floor area
- Formula/methode: `floor_area * storeys`
- Resultaat: **140.0 m2**
- Model: BLD-EXTENSION, L00, L01
- Tekeningen: A-101, A-102
- Rapporten: R-001, R-101
- REQ: REQ-102
- Status: SIMULATION_ONLY

### CAL-A03 — Extension enclosed volume
- Formula/methode: `floor_area * storey_height * storeys`
- Resultaat: **448.0 m3**
- Model: BLD-EXTENSION
- Tekeningen: A-201, A-301
- Rapporten: R-101
- REQ: REQ-102
- Status: SIMULATION_ONLY

### CAL-A04 — Existing gross floor area
- Formula/methode: `existing_width * existing_length * storeys`
- Resultaat: **336.0 m2**
- Model: BLD-EXISTING
- Tekeningen: A-101, A-102
- Rapporten: R-101
- REQ: REQ-102
- Status: SIMULATION_ONLY

### CAL-A05 — Total gross floor area
- Formula/methode: `existing_gross_area + extension_gross_area`
- Resultaat: **476.0 m2**
- Model: BLD-EXISTING, BLD-EXTENSION
- Tekeningen: A-101, A-102
- Rapporten: R-001
- REQ: REQ-102
- Status: SIMULATION_ONLY

### CAL-A06 — Modelled net space area
- Formula/methode: `sum(space.area_m2)`
- Resultaat: **388.32 m2**
- Model: SP-L00-01, SP-L00-02, SP-L00-03, SP-L00-04, SP-L00-05, SP-L00-06, SP-L01-01, SP-L01-02, SP-L01-03, SP-L01-04, SP-L01-05, SP-L01-06
- Tekeningen: A-101, A-102
- Rapporten: R-101
- REQ: REQ-102
- Status: SIMULATION_ONLY

## Structural Loads

### CAL-S01 — Service floor load per storey
- Formula/methode: `floor_area * floor_area_load`
- Resultaat: **490.0 kN**
- Model: BLD-EXTENSION
- Tekeningen: S-201
- Rapporten: R-201
- REQ: REQ-103
- Status: SIMULATION_ONLY

### CAL-S02 — Service roof load
- Formula/methode: `roof_area * roof_area_load`
- Resultaat: **245.0 kN**
- Model: BLD-EXTENSION, LRF
- Tekeningen: A-401, S-201
- Rapporten: R-201
- REQ: REQ-103
- Status: SIMULATION_ONLY

### CAL-S03 — Total service gravity load
- Formula/methode: `floor_area * floor_load * storeys + roof_area * roof_load + wall_allowance`
- Resultaat: **1335.0 kN**
- Model: BLD-EXTENSION
- Tekeningen: S-201
- Rapporten: R-201
- REQ: REQ-103
- Status: SIMULATION_ONLY

## Load Path

### CAL-S04 — Average column reaction
- Formula/methode: `total_service_load / column_count`
- Resultaat: **148.33 kN**
- Model: CONN-001, CONN-002, CONN-003, CONN-004
- Tekeningen: S-201
- Rapporten: R-201
- REQ: REQ-103
- Status: SIMULATION_ONLY

### CAL-S05 — Representative beam line load
- Formula/methode: `floor_area_load * tributary_width`
- Resultaat: **24.5 kN/m**
- Model: BLD-EXTENSION
- Tekeningen: S-201
- Rapporten: R-201
- REQ: REQ-103
- Status: SIMULATION_ONLY

### CAL-S06 — Representative simple-span moment
- Formula/methode: `line_load * span^2 / 8`
- Resultaat: **76.56 kNm**
- Model: BLD-EXTENSION
- Tekeningen: S-201
- Rapporten: R-201
- REQ: REQ-103
- Status: SIMULATION_ONLY

### CAL-S07 — Representative support reaction
- Formula/methode: `line_load * span / 2`
- Resultaat: **61.25 kN**
- Model: BLD-EXTENSION
- Tekeningen: S-201
- Rapporten: R-201
- REQ: REQ-103
- Status: SIMULATION_ONLY

## Foundation

### CAL-F01 — Assumed bearing area
- Formula/methode: `strip_width * total_strip_length`
- Resultaat: **72.0 m2**
- Model: BLD-EXTENSION
- Tekeningen: S-101
- Rapporten: R-201
- REQ: REQ-104
- Status: SIMULATION_ONLY

### CAL-F02 — Indicative average contact pressure
- Formula/methode: `total_service_load / bearing_area`
- Resultaat: **18.54 kPa**
- Model: BLD-EXTENSION
- Tekeningen: S-101
- Rapporten: R-201
- REQ: REQ-104
- Status: SIMULATION_ONLY

## Egress

### CAL-E01 — Total simulated exit width
- Formula/methode: `exit_count * exit_width_each`
- Resultaat: **2.4 m**
- Model: BLD-EXTENSION
- Tekeningen: F-101
- Rapporten: R-301
- REQ: REQ-105
- Status: SIMULATION_ONLY

### CAL-E02 — Persons per simulated exit
- Formula/methode: `peak_occupancy / exit_count`
- Resultaat: **100.0 persons/exit**
- Model: BLD-EXTENSION
- Tekeningen: F-101
- Rapporten: R-301
- REQ: REQ-105, REQ-107
- Status: SIMULATION_ONLY

### CAL-E03 — Persons per metre total exit width
- Formula/methode: `peak_occupancy / total_exit_width`
- Resultaat: **83.33 persons/m**
- Model: BLD-EXTENSION
- Tekeningen: F-101
- Rapporten: R-301
- REQ: REQ-105, REQ-107
- Status: SIMULATION_ONLY

## Ventilation

### CAL-V01 — Ventilation flow regular_future
- Formula/methode: `persons * rate_l_s_person * 3.6`
- Resultaat: **3780.0 m3/h**
- Model: BLD-EXISTING, BLD-EXTENSION
- Tekeningen: A-101, A-102
- Rapporten: R-301
- REQ: REQ-105, REQ-107
- Status: SIMULATION_ONLY

### CAL-V02 — Ventilation flow friday_future
- Formula/methode: `persons * rate_l_s_person * 3.6`
- Resultaat: **3150.0 m3/h**
- Model: BLD-EXISTING, BLD-EXTENSION
- Tekeningen: A-101, A-102
- Rapporten: R-301
- REQ: REQ-105, REQ-107
- Status: SIMULATION_ONLY

### CAL-V03 — Ventilation flow special_peak
- Formula/methode: `persons * rate_l_s_person * 3.6`
- Resultaat: **5040.0 m3/h**
- Model: BLD-EXISTING, BLD-EXTENSION
- Tekeningen: A-101, A-102
- Rapporten: R-301
- REQ: REQ-105, REQ-107
- Status: SIMULATION_ONLY

## Parking

### CAL-P01 — Available spaces regular_weekday
- Formula/methode: `capacity - occupied`
- Resultaat: **115.0 spaces**
- Model: P-A, P-B, P-C, P-D, P-E
- Tekeningen: A-001
- Rapporten: R-401
- REQ: REQ-106
- Status: SIMULATION_ONLY

### CAL-P02 — Available spaces friday_pre_peak
- Formula/methode: `capacity - occupied`
- Resultaat: **90.0 spaces**
- Model: P-A, P-B, P-C, P-D, P-E
- Tekeningen: A-001
- Rapporten: R-401
- REQ: REQ-106
- Status: SIMULATION_ONLY

### CAL-P03 — Available spaces friday_prayer_peak
- Formula/methode: `capacity - occupied`
- Resultaat: **55.0 spaces**
- Model: P-A, P-B, P-C, P-D, P-E
- Tekeningen: A-001
- Rapporten: R-401
- REQ: REQ-106
- Status: SIMULATION_ONLY

### CAL-P04 — Available spaces saturday_active_use
- Formula/methode: `capacity - occupied`
- Resultaat: **80.0 spaces**
- Model: P-A, P-B, P-C, P-D, P-E
- Tekeningen: A-001
- Rapporten: R-401
- REQ: REQ-106
- Status: SIMULATION_ONLY

### CAL-P05 — Available spaces sunday_active_use
- Formula/methode: `capacity - occupied`
- Resultaat: **100.0 spaces**
- Model: P-A, P-B, P-C, P-D, P-E
- Tekeningen: A-001
- Rapporten: R-401
- REQ: REQ-106
- Status: SIMULATION_ONLY

### CAL-P06 — Synthetic parking surplus regular_future
- Formula/methode: `minimum_available - demand`
- Resultaat: **25.0 spaces**
- Model: P-A, P-B, P-C, P-D, P-E
- Tekeningen: A-001
- Rapporten: R-401
- REQ: REQ-106
- Status: SIMULATION_ONLY

### CAL-P07 — Synthetic parking surplus friday_future
- Formula/methode: `minimum_available - demand`
- Resultaat: **30.0 spaces**
- Model: P-A, P-B, P-C, P-D, P-E
- Tekeningen: A-001
- Rapporten: R-401
- REQ: REQ-106
- Status: SIMULATION_ONLY

### CAL-P08 — Synthetic parking surplus special_peak
- Formula/methode: `minimum_available - demand`
- Resultaat: **15.0 spaces**
- Model: P-A, P-B, P-C, P-D, P-E
- Tekeningen: A-001
- Rapporten: R-401
- REQ: REQ-106
- Status: SIMULATION_ONLY

## Construction Activity

### CAL-C01 — Construction-phase duration
- Formula/methode: `sum(duration_days excluding operational use)`
- Resultaat: **95.0 days**
- Model: BLD-EXTENSION
- Tekeningen: X-101
- Rapporten: R-501
- REQ: REQ-108
- Status: SIMULATION_ONLY

### CAL-C02 — Synthetic equipment operating hours
- Formula/methode: `sum(equipment operating_hours)`
- Resultaat: **496.0 h**
- Model: BLD-EXTENSION
- Tekeningen: X-101
- Rapporten: R-501
- REQ: REQ-108
- Status: SIMULATION_ONLY

### CAL-C03 — Synthetic transport activity
- Formula/methode: `sum(movements * distance_km)`
- Resultaat: **6600.0 vehicle-km**
- Model: BLD-EXTENSION
- Tekeningen: X-101
- Rapporten: R-501
- REQ: REQ-108
- Status: SIMULATION_ONLY

