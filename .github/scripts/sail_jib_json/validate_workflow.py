"""Validate the structure and safety gates of sail-jib-json publication."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml


WORKFLOW = Path(".github/workflows/build-sail-jib-json.yml")

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
    assert build.get("runs-on") == "windows-2025"
    assert "strategy" not in build

    publish = mapping(jobs["test-and-publish"], "test-and-publish job")
    assert publish.get("needs") == "build"

    source = WORKFLOW.read_text(encoding="utf-8")
    assert source.count("repository: VIDLG/sail-jib-json") == 2
    assert source.count("ref: ${{ inputs.source_ref }}") == 2
    assert "submodules: recursive" in source
    assert "SAIL_JIB_JSON_VERSION: ${{ inputs.version }}" in source
    assert "run: pixi run conda-package" in source
    assert "manifest-path: channel/pixi.toml" in source
    assert source.count("pixi run --manifest-path channel/pixi.toml python") == 4
    assert source.count("uses: actions/download-artifact@v8") == 1
    assert source.count("if: inputs.publish") == 2
    assert "release.py validate-request" in source
    assert source.count("release.py validate-source") == 2
    assert "release.py verify-packages" in source
    assert "release.py publish-packages" in source
    assert "release.py commit-channel" in source
    assert "linux-64" not in source
    assert "linux-aarch64" not in source
    assert "run: |" not in source

    print("sail-jib-json workflow validation passed")


if __name__ == "__main__":
    main()
