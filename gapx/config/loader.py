"""Configuration loading utilities."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback implemented below
    yaml = None
from pydantic import BaseModel

from .models import (
    GAConfig,
    EssentialityConfig,
    GenomicEvidenceConfig,
    InputsConfig,
    ModelSourcesConfig,
    OmicsConfig,
    RunBundle,
    ScoringConfig,
    TasksConfig,
    ThermoConfig,
)

def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        text = handle.read()
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _fallback_yaml_load(text)


def _unwrap_section(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    section = data.get(key)
    if isinstance(section, dict):
        return section
    return data


def _fallback_yaml_load(text: str) -> Dict[str, Any]:
    """Very small YAML loader supporting the subset used in examples."""

    lines = text.splitlines()

    def parse_block(index: int, indent: int):
        result: Any = None
        while index < len(lines):
            raw = lines[index]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                index += 1
                continue
            current_indent = len(raw) - len(raw.lstrip(" "))
            if current_indent < indent:
                break
            if stripped.startswith("- "):
                if result is None:
                    result = []
                elif not isinstance(result, list):
                    raise ValueError("Mixed list/dict structures are not supported in fallback YAML parser")
                value_str = stripped[2:].strip()
                if value_str:
                    if ":" in value_str and not value_str.startswith("{"):
                        key, rest = value_str.split(":", 1)
                        entry: Dict[str, Any] = {key.strip(): _parse_scalar(rest.strip())}
                        index += 1
                        child, index = parse_block(index, current_indent + 2)
                        if isinstance(child, dict):
                            entry.update(child)
                        elif child not in (None, {}):
                            raise ValueError("List item expected mapping in fallback YAML parser")
                        result.append(entry)
                    else:
                        result.append(_parse_scalar(value_str))
                        index += 1
                else:
                    value, index = parse_block(index + 1, current_indent + 2)
                    result.append(value)
            else:
                if result is None:
                    result = {}
                elif not isinstance(result, dict):
                    raise ValueError("Mixed list/dict structures are not supported in fallback YAML parser")
                if ":" not in stripped:
                    raise ValueError(f"Invalid YAML line: {stripped}")
                key, rest = stripped.split(":", 1)
                key = key.strip().strip('"')
                rest = rest.strip()
                if rest:
                    result[key] = _parse_scalar(rest)
                    index += 1
                else:
                    value, index = parse_block(index + 1, current_indent + 2)
                    result[key] = value
        if result is None:
            result = {}
        return result, index

    data, _ = parse_block(0, 0)
    if not isinstance(data, dict):
        raise ValueError("Root of YAML document must be a mapping in fallback loader")
    return data


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"null", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.startswith("{") and value.endswith("}"):
        return _parse_inline_structure(value)
    if value.startswith("[") and value.endswith("]"):
        return _parse_inline_structure(value)
    try:
        if "." in value or "e" in lowered:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_inline_structure(value: str) -> Any:
    value = _normalise_inline(value)
    return ast.literal_eval(value)


def _normalise_inline(value: str) -> str:
    replacements = {
        "true": "True",
        "false": "False",
        "null": "None",
    }

    def replace_match(match: re.Match[str]) -> str:
        return f"{match.group(1)}'{match.group(2)}':"

    normalised = re.sub(r"([\{,]\s*)([A-Za-z0-9_]+)\s*:", replace_match, value)
    for yaml_word, py_word in replacements.items():
        normalised = re.sub(rf"\b{yaml_word}\b", py_word, normalised)
    return normalised


def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        text = handle.read()
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _fallback_yaml_load(text)


def load_config(path: str | Path) -> RunBundle:
    """Load a root configuration file and resolve referenced sub-configs."""

    path = Path(path)
    root_data = _read_yaml(path)
    bundle = RunBundle.parse_obj(root_data)

    base_dir = path.parent
    inputs: InputsConfig = bundle.inputs

    def _load_optional(
        loader: Callable[[Dict[str, Any]], BaseModel], ref: Optional[Path]
    ) -> Optional[BaseModel]:
        if ref is None:
            return None
        return loader(_read_yaml(base_dir / ref))

    bundle.model_sources = ModelSourcesConfig.parse_obj(
        _read_yaml(base_dir / inputs.model_sources)
    )
    bundle.tasks = TasksConfig.parse_obj(_read_yaml(base_dir / inputs.tasks))
    bundle.ga = GAConfig.parse_obj(
        _unwrap_section(_read_yaml(base_dir / inputs.ga), "ga")
    )
    bundle.thermo = ThermoConfig.parse_obj(
        _unwrap_section(_read_yaml(base_dir / inputs.thermo), "thermo")
    )
    bundle.genomic_evidence = GenomicEvidenceConfig.parse_obj(
        _unwrap_section(_read_yaml(base_dir / inputs.genomic_evidence), "genomic_evidence")
    )
    bundle.scoring = ScoringConfig.parse_obj(_read_yaml(base_dir / inputs.scoring))
    bundle.essentiality = _load_optional(
        lambda data: EssentialityConfig.parse_obj(_unwrap_section(data, "essentiality")),
        inputs.essentiality,
    )
    bundle.omics = _load_optional(
        lambda data: OmicsConfig.parse_obj(_unwrap_section(data, "omics")),
        inputs.omics,
    )

    return bundle


def dump_manifest(bundle: RunBundle, path: str | Path) -> None:
    """Persist a run manifest capturing resolved configuration and metadata."""

    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(bundle.json())
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def load_manifest(path: str | Path) -> RunBundle:
    """Load a previously generated manifest."""

    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return RunBundle.parse_obj(data)

