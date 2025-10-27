"""Pydantic models describing GAPx configuration schemas."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field, validator


class ParallelConfig(BaseModel):
    """Parallel execution settings for island model GA."""

    islands: int = Field(1, ge=1)
    workers_per_island: int = Field(1, ge=1)
    migration_interval: int = Field(20, ge=1)
    migrants: int = Field(1, ge=0)


class RunConfig(BaseModel):
    """Top-level run metadata."""

    name: str
    seed: int = 42
    output_dir: Path
    device: Literal["cpu", "cuda"] = "cpu"
    parallel: ParallelConfig = Field(default_factory=ParallelConfig)

    @validator("output_dir", pre=True)
    def _coerce_path(cls, value: Path | str) -> Path:
        return Path(value)


class ModelSource(BaseModel):
    path: Path
    kind: Literal["sbml", "json"] = "sbml"

    @validator("path", pre=True)
    def _coerce_path(cls, value: Path | str) -> Path:
        return Path(value)


class ReactionDefinition(BaseModel):
    id: str
    stoichiometry: Dict[str, float]
    lb: float = -1000.0
    ub: float = 1000.0
    genes: Sequence[str] = Field(default_factory=tuple)
    subsystem: Optional[str] = None


class CandidateDatabase(BaseModel):
    reactions: List[ReactionDefinition] = Field(default_factory=list)
    source: Literal["bigg", "vmh", "custom"] = "custom"


class ModelFilters(BaseModel):
    drop_if_no_genomic_evidence: bool = False
    drop_if_far_from_tasks: bool = False


class ModelSourcesConfig(BaseModel):
    template_model: ModelSource
    candidate_database: CandidateDatabase
    filters: ModelFilters = Field(default_factory=ModelFilters)


class MediaConfig(BaseModel):
    set_exchange: Dict[str, float] = Field(default_factory=dict)
    close_others: bool = True


class FluxThreshold(BaseModel):
    rxn: str
    min: Optional[float] = None
    max: Optional[float] = None


class OutputCheck(BaseModel):
    flux_thresholds: List[FluxThreshold] = Field(default_factory=list)


class TaskConstraint(BaseModel):
    rxn: str
    lb: Optional[float] = None
    ub: Optional[float] = None


class TaskDefinition(BaseModel):
    id: str
    category: Literal["essential", "basic", "auxiliary"] = "basic"
    media: MediaConfig
    objective: str
    objective_sense: Literal["max", "min"] = "max"
    min_objective_value: Optional[float] = None
    constraints: List[TaskConstraint] = Field(default_factory=list)
    outputs_check: Optional[OutputCheck] = None


class TasksConfig(BaseModel):
    tasks: List[TaskDefinition]


class ThermoConfig(BaseModel):
    enabled: bool = False
    loopless: bool = False
    temperature_K: float = 310.15
    currency_pairs: Dict[str, List[str]] = Field(default_factory=dict)
    infeasible_action: Literal["penalize", "repair_only", "penalize_and_repair"] = (
        "penalize"
    )
    loop_penalty: float = 0.0


class EvidenceWeights(BaseModel):
    annotation: float = 1.0
    homology: float = 0.0
    phylogeny: float = 0.0
    transcript_support: float = 0.0
    proteome_support: float = 0.0


class EvidenceEntry(BaseModel):
    reaction_id: str
    annotation: bool = False
    homology_bitscore: Optional[float] = None
    phylogeny_distance: Optional[float] = None
    transcript_tpm: Optional[float] = None
    protein_detected: Optional[bool] = None


class GenomicEvidenceConfig(BaseModel):
    weights: EvidenceWeights = Field(default_factory=EvidenceWeights)
    entries: List[EvidenceEntry] = Field(default_factory=list)


class PenaltyConfig(BaseModel):
    hard_constraint_violation: float = 0.0
    minor_violation: float = 0.0


class FitnessWeights(BaseModel):
    task: float = 1.0
    parsimony: float = 0.0
    genomic: float = 0.0
    thermo: float = 0.0


class FitnessConfig(BaseModel):
    mode: Literal["weighted_sum", "pareto"] = "weighted_sum"
    weights: FitnessWeights = Field(default_factory=FitnessWeights)
    penalties: PenaltyConfig = Field(default_factory=PenaltyConfig)


class ParsimonyConfig(BaseModel):
    target: Literal["min_reactions", "min_added", "min_total_flux"] = "min_reactions"
    normalize_by_template_size: bool = False


class ScoringConfig(BaseModel):
    fitness: FitnessConfig = Field(default_factory=FitnessConfig)
    parsimony: ParsimonyConfig = Field(default_factory=ParsimonyConfig)


class SelectionConfig(BaseModel):
    type: Literal["tournament", "roulette", "rank"] = "tournament"
    k: int = 3
    elitism: int = 0


class UniformCrossoverConfig(BaseModel):
    type: Literal["uniform"] = "uniform"
    p: float = Field(0.5, ge=0.0, le=1.0)


class PathwayAwareConfig(BaseModel):
    enabled: bool = False
    block_size: Optional[Literal["auto"] | int] = None


class CrossoverConfig(BaseModel):
    template_region: UniformCrossoverConfig = Field(default_factory=UniformCrossoverConfig)
    database_region: UniformCrossoverConfig = Field(default_factory=UniformCrossoverConfig)
    pathway_aware: PathwayAwareConfig = Field(default_factory=PathwayAwareConfig)


class PathwayMutationConfig(BaseModel):
    enabled: bool = False
    p_pathway: float = 0.0


class AdaptiveMutationConfig(BaseModel):
    stagnation_window: int = 10
    scale_up: float = 1.0
    max_bitflip_p: float = 0.05


class MutationConfig(BaseModel):
    bitflip_p: float = 0.0
    pathway_mutation: PathwayMutationConfig = Field(default_factory=PathwayMutationConfig)
    adaptive: AdaptiveMutationConfig = Field(default_factory=AdaptiveMutationConfig)


class RepairConfig(BaseModel):
    milp_min_additions: bool = False
    loopless_check: bool = False
    max_milp_time_s: Optional[int] = None


class ConstraintsConfig(BaseModel):
    enforce_task_pass_for: List[str] = Field(default_factory=list)
    repair: RepairConfig = Field(default_factory=RepairConfig)


class InitPopulationMix(BaseModel):
    random: float = 1.0
    conservative_template_keep: float = 0.0
    evidence_only: float = 0.0
    minimal_task_only: float = 0.0

    @validator("random", "conservative_template_keep", "evidence_only", "minimal_task_only")
    def _validate_probability(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError("mix fractions must be non-negative")
        return value


class GAConfig(BaseModel):
    population: int = 100
    generations: int = 100
    selection: SelectionConfig = Field(default_factory=SelectionConfig)
    crossover: CrossoverConfig = Field(default_factory=CrossoverConfig)
    mutation: MutationConfig = Field(default_factory=MutationConfig)
    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    init_population_mix: InitPopulationMix = Field(default_factory=InitPopulationMix)


class EssentialityConfig(BaseModel):
    model_gene_to_truth: Dict[str, Literal["essential", "nonessential"]] = Field(
        default_factory=dict
    )


class OmicsIntegrationConfig(BaseModel):
    method: Literal["GIMME", "iMAT", "GIM3E"] = "GIMME"
    thresholds: Dict[str, float] = Field(default_factory=dict)


class TranscriptomicsConfig(BaseModel):
    file: Path
    gene_col: str
    value_col: str
    condition: Optional[str] = None

    @validator("file", pre=True)
    def _coerce_path(cls, value: Path | str) -> Path:
        return Path(value)


class OmicsConfig(BaseModel):
    transcriptomics: Optional[TranscriptomicsConfig] = None
    integration: Optional[OmicsIntegrationConfig] = None


class ExportModelConfig(BaseModel):
    formats: List[Literal["sbml", "json"]] = Field(default_factory=lambda: ["sbml"])
    path: Path

    @validator("path", pre=True)
    def _coerce_path(cls, value: Path | str) -> Path:
        return Path(value)


class ReportsConfig(BaseModel):
    html: bool = True
    json: bool = True


class ExportConfig(BaseModel):
    best_model: ExportModelConfig
    reports: ReportsConfig = Field(default_factory=ReportsConfig)


class RunBundle(BaseModel):
    run: RunConfig
    inputs: "InputsConfig"
    export: ExportConfig
    model_sources: Optional[ModelSourcesConfig] = None
    tasks: Optional[TasksConfig] = None
    thermo: Optional[ThermoConfig] = None
    genomic_evidence: Optional[GenomicEvidenceConfig] = None
    scoring: Optional[ScoringConfig] = None
    ga: Optional[GAConfig] = None
    essentiality: Optional[EssentialityConfig] = None
    omics: Optional[OmicsConfig] = None


class InputsConfig(BaseModel):
    model_sources: Path
    tasks: Path
    ga: Path
    thermo: Path
    genomic_evidence: Path
    scoring: Path
    omics: Optional[Path] = None
    essentiality: Optional[Path] = None

    @validator("model_sources", "tasks", "ga", "thermo", "genomic_evidence", "scoring", "omics", "essentiality", pre=True)
    def _coerce_paths(cls, value: Optional[Path | str]) -> Optional[Path]:
        if value is None:
            return None
        return Path(value)


RunBundle.update_forward_refs()

