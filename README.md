# GAPx

GAPx is a GA-based framework for integrated gap-filling and pruning of genome-scale metabolic models (GEMs).

This repository contains the initial codebase scaffold that follows the provided Product Design Requirements. The
focus of this iteration is configuration management, CLI entry points, and extensible module boundaries that can be
expanded with COBRApy-based optimisation, genetic operators, and reporting utilities.

## Features

- YAML-based configuration with schema validation using Pydantic models
- Modular package layout separating I/O, tasks, fitness, GA, repair, evaluation, and parallel orchestration concerns
- Rich CLI implemented with [Typer](https://typer.tiangolo.com/) offering `validate`, `run`, and `report` commands
- Deterministic run manifests and logging primitives prepared for future integration
- Example configuration bundle mirroring the specification for quick experimentation

## Getting Started

Install dependencies in a Python 3.10+ environment:

```bash
pip install -e .
```

Validate a configuration bundle:

```bash
gapx validate --run examples/config/run.yaml
```

Run a GA experiment (skeleton implementation; heavy lifting to be implemented in future milestones):

```bash
gapx run --run examples/config/run.yaml
```

Generate a report placeholder from a manifest:

```bash
gapx report --run runs/demo/manifest.json --format html
```

## Tests

```bash
pytest
```

