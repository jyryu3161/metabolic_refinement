from pathlib import Path

from gapx.config.loader import load_config


def test_load_example_bundle(tmp_path: Path) -> None:
    run_config = Path(__file__).parent.parent / "examples" / "config" / "run.yaml"
    bundle = load_config(run_config)

    assert bundle.run.name == "ecoli_gapx_demo"
    assert bundle.ga.generations == 150
    assert bundle.tasks is not None
    assert len(bundle.tasks.tasks) == 2

