# OpenSees Integration Architecture

BB13 adds structural analysis to Phoenix.

The adapter supports two modes:

- native OpenSeesPy mode when available;
- deterministic offline 2D truss verification mode.

The offline solver is intentionally limited and provides installation,
integration and equilibrium verification. Advanced frame, nonlinear, modal and
dynamic analyses are scheduled for later OpenSees expansion blocks.
