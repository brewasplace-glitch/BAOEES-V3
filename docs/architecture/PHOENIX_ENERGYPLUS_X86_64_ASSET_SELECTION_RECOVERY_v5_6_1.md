# EnergyPlus x86-64 Asset Selection Recovery v5.6.1

## Confirmed failure

v5.6.0 selected the official Windows ARM64 installer:

`EnergyPlus-26.1.0-6f2e40d102-Windows-arm64.exe`

The user's computer requires the Windows x86-64/AMD64 asset.

## Recovery

v5.6.1 accepts an installer only when:

1. the asset name contains `Windows-x86_64`;
2. the asset name does not contain `arm64`;
3. the official GitHub asset SHA-256 digest matches;
4. the downloaded PE machine code equals `0x8664` (AMD64);
5. the installed `energyplus.exe` reports EnergyPlus 26.1.0.

The repository remains untouched until installation and a real design-day
simulation have succeeded.
