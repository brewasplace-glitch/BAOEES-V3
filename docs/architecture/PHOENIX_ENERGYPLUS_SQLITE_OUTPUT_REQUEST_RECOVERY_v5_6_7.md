# EnergyPlus SQLite Output Request Recovery v5.6.7

Phoenix appends `Output:SQLite, SimpleAndTabular;` to the copied acceptance
IDF when absent. Acceptance requires non-empty ERR, END and SQL files, zero
Severe/Fatal errors, `energyplus: AVAILABLE`, commit, push and final clean
synchronization. The existing EnergyPlus 26.1.0 installation is reused.
