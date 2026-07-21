# Phoenix Structural Solver Contract Adapter â€” Wave 8 v1.0

Wave 8 converts the verified structural bootstrap model into an explicit
solver contract.

The contract registers:

- support and boundary conditions;
- nodal actions;
- analysis type;
- solver identity and version;
- convergence tolerance;
- maximum iterations;
- total, restrained and free degrees of freedom.

All node and load-case references are verified against the Wave 7 artifact.

Wave 8 does not execute a finite-element solver. It therefore leaves reactions,
displacements, member forces, eigenvalues and convergence results unset. A
future solver-specific adapter may consume this contract, export an engine
input deck, execute the engine, verify the exit status and import traceable
results.
