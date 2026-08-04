"""Run the package-pin Python smoke test against locally built conda packages."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


EXPECTED_PYTHON_VERSIONS = {"3.13"}
PACKAGE_PATTERN = re.compile(
    r"^verylogic-nextpnr-(?P<version>.+)-py(?P<python>\d+)h[0-9a-f]+_\d+\.conda$"
)
TARGET_COMMANDS = (
    ("nextpnr-ice40", "--arch.type", "lp384", "--arch.package", "qn32"),
    ("nextpnr-ice40", "--arch.type", "lp1k", "--arch.package", "tq144"),
    ("nextpnr-ice40", "--arch.type", "u4k", "--arch.package", "sg48"),
    ("nextpnr-ice40", "--arch.type", "up5k", "--arch.package", "sg48"),
    ("nextpnr-ice40", "--arch.type", "hx8k", "--arch.package", "ct256"),
    ("nextpnr-himbaechel", "--device", "GW1N-LV1QN48C6/I5"),
    ("nextpnr-himbaechel", "--device", "GW5A-LV25LQ100C1/I0"),
    ("nextpnr-himbaechel", "--device", "xc7a100tcsg324-1"),
)


def find_variants(output_dir: Path, expected_version: str) -> dict[str, Path]:
    variants: dict[str, Path] = {}
    for package in sorted((output_dir / "win-64").glob("verylogic-nextpnr-*.conda")):
        match = PACKAGE_PATTERN.fullmatch(package.name)
        if match is None:
            raise SystemExit(f"unexpected package filename: {package.name}")
        if match.group("version") != expected_version:
            raise SystemExit(
                f"expected package version {expected_version}, found {match.group('version')}"
            )
        digits = match.group("python")
        python_version = f"{digits[0]}.{digits[1:]}"
        if python_version in variants:
            raise SystemExit(f"duplicate Python {python_version} package")
        variants[python_version] = package.resolve()

    if set(variants) != EXPECTED_PYTHON_VERSIONS:
        expected = sorted(EXPECTED_PYTHON_VERSIONS)
        found = sorted(variants)
        raise SystemExit(f"expected Python variants {expected}, found {found}")
    return variants


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: test_verylogic_nextpnr_package_pins.py OUTPUT_DIR PACKAGE_VERSION SMOKE_SCRIPT"
        )

    output_dir = Path(sys.argv[1]).resolve()
    package_version = sys.argv[2]
    smoke_script = Path(sys.argv[3]).resolve()
    if not smoke_script.is_file():
        raise SystemExit(f"package-pin smoke script not found: {smoke_script}")

    variants = find_variants(output_dir, package_version)
    channel = output_dir / "package-pin-test-channel"
    shutil.rmtree(channel, ignore_errors=True)
    _ = subprocess.run(
        [
            "rattler-build",
            "publish",
            *(str(package) for package in variants.values()),
            "--to",
            channel.as_uri(),
        ],
        check=True,
    )

    backend_commands = [
        [*target, "--run", str(smoke_script)] for target in TARGET_COMMANDS
    ]
    smoke_command = " && ".join(
        subprocess.list2cmdline(command) for command in backend_commands
    )

    for python_version in sorted(variants):
        _ = subprocess.run(
            [
                "pixi",
                "exec",
                "--force-reinstall",
                "--channel",
                channel.as_uri(),
                "--channel",
                "conda-forge",
                "--spec",
                f"python=={python_version}",
                "--spec",
                f"verylogic-nextpnr=={package_version}",
                "cmd.exe",
                "/d",
                "/s",
                "/c",
                smoke_command,
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
