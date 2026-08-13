# PROJECT PHOENIX — CalculiX Reaction & Equilibrium Hardening v1.1

Required baseline: `e85f1b1078594a43837bee6cfe8b5bbb0f630a87`

The live Golden Reference run completed successfully but the original parser did not recognize
CalculiX' `total force (fx,fy,fz)` DAT block.

Observed raw evidence:
- support node 1: +2475 N Z
- support node 101: +2475 N Z
- support-set total: +4950 N Z

The generated input deck contains:
- -25 N CLOAD at node 1
- -25 N CLOAD at node 101
- -50 N at each of the 99 interior nodes
- total vertical CLOAD: -5000 N

v1.1 preserves the solver output and performs explicit constrained-support load accounting:

`R_full = F_reported_support - P_direct_on_support`

So:
- total: 4950 - (-50) = 5000 N
- each support: 2475 - (-25) = 2500 N
- global vertical balance error = 0 N

The new runner reevaluates the existing DAT and INP without starting CalculiX again.

Safety:
- raw solver evidence is not modified
- software tolerance is not a general engineering tolerance
- professional approval is not automatic
- code compliance is not automatic
- Production and FOR-CONSTRUCTION remain LOCKED
