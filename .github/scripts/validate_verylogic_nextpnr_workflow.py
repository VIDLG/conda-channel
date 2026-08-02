"""Validate the structure of the verylogic-nextpnr publishing workflow."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml


WORKFLOW = Path(".github/workflows/build-verylogic-nextpnr.yml")
EXPECTED_VARIANTS = {("3.12", "py312"), ("3.13", "py313")}


def mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a mapping")
    return cast(dict[str, object], value)


def main() -> None:
    loaded = cast(object, yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")))
    document = mapping(loaded, "workflow")
    jobs = mapping(document.get("jobs"), "jobs")
    assert set(jobs) == {"validate", "build", "test-and-publish"}

    build = mapping(jobs["build"], "build job")
    assert build.get("needs") == "validate"
    build_env = mapping(build.get("env"), "build env")
    assert build_env.get("VERYLOGIC_CONDA_OUTPUT") == "D:\\b"
    strategy = mapping(build.get("strategy"), "build strategy")
    matrix = mapping(strategy.get("matrix"), "build matrix")
    include = matrix.get("include")
    if not isinstance(include, list):
        raise TypeError("build matrix include must be a list")
    include_items = cast(list[object], include)
    variants: set[tuple[str, str]] = set()
    for index, item in enumerate(include_items):
        variant = mapping(item, f"build matrix include[{index}]")
        variants.add((str(variant.get("python")), str(variant.get("tag"))))
    assert variants == EXPECTED_VARIANTS

    test_and_publish = mapping(jobs["test-and-publish"], "test-and-publish job")
    assert test_and_publish.get("needs") == "build"
    test_env = mapping(test_and_publish.get("env"), "test-and-publish env")
    assert test_env.get("VERYLOGIC_CONDA_OUTPUT") == "D:\\b"

    source = WORKFLOW.read_text(encoding="utf-8")
    assert "pixi run --manifest-path pixi.toml --environment conda-package just conda-build ${{ matrix.python }}" in source
    assert "uses: actions/download-artifact@v8" in source
    assert "merge-multiple: true" in source
    assert "pixi run --environment conda-package just conda-test" in source
    assert "if: inputs.publish" in source
    assert "publish=true requires source_ref v$env:PACKAGE_VERSION" in source
    assert "startsWith(inputs.source_ref, 'v') && inputs.source_ref || 'main'" in source

    print("verylogic-nextpnr workflow validation passed")


if __name__ == "__main__":
    main()
