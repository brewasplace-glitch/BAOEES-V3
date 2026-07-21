"""Phoenix discipline adapter package."""

from .gis_bootstrap import (
    GISBootstrapConfig,
    GISBootstrapError,
    GISBootstrapSource,
    create_gis_bootstrap_adapter,
)
from .geotechnical_bootstrap import (
    GeotechnicalBootstrapConfig,
    GeotechnicalBootstrapError,
    SoilLayer,
    create_geotechnical_bootstrap_adapter,
)

__all__ = [
    "GISBootstrapConfig",
    "GISBootstrapError",
    "GISBootstrapSource",
    "create_gis_bootstrap_adapter",
    "GeotechnicalBootstrapConfig",
    "GeotechnicalBootstrapError",
    "SoilLayer",
    "create_geotechnical_bootstrap_adapter",
]

from .foundation_bootstrap import (
    FoundationBootstrapConfig,
    FoundationBootstrapError,
    create_foundation_bootstrap_adapter,
)

from .structural_analysis_bootstrap import (
    StructuralBootstrapConfig,
    StructuralBootstrapError,
    StructuralElement,
    StructuralLoadCase,
    StructuralLoadCombination,
    StructuralMaterial,
    create_structural_analysis_bootstrap_adapter,
)

from .structural_solver_contract import (
    BoundaryCondition,
    NodalAction,
    StructuralSolverContractConfig,
    StructuralSolverContractError,
    create_structural_solver_contract_adapter,
)

from .reference_solver_execution import (
    ReferenceSolverExecutionConfig,
    ReferenceSolverExecutionError,
    create_reference_solver_execution_adapter,
)

from .concrete_axial_design import (
    ConcreteAxialDesignConfig,
    ConcreteAxialDesignError,
    ConcreteMemberDesignInput,
    create_concrete_axial_design_adapter,
)

from .steel_axial_design import (
    SteelAxialDesignConfig,
    SteelAxialDesignError,
    SteelMemberDesignInput,
    create_steel_axial_design_adapter,
)

from .timber_masonry_axial_design import (
    TimberMasonryAxialDesignConfig,
    TimberMasonryAxialDesignError,
    TimberMasonryMemberDesignInput,
    create_timber_masonry_axial_design_adapter,
)

from .bim_ifc_synchronization import (
    BIMIFCSynchronizationConfig,
    BIMIFCSynchronizationError,
    create_bim_ifc_synchronization_adapter,
)

from .automatic_drawing_generation import (
    AutomaticDrawingGenerationConfig,
    AutomaticDrawingGenerationError,
    create_automatic_drawing_generation_adapter,
)
