"""Channel-owned validation and publication policy for sail-jib-json."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn


PACKAGE_NAME = "sail-jib-json"
EXPECTED_SUBDIRS = ("win-64",)
FULL_COMMIT = re.compile(r"^[0-9a-fA-F]{40}$")


class ReleaseError(RuntimeError):
    """A requested channel operation violates the publication contract."""


def fail(message: str) -> NoReturn:
    raise ReleaseError(message)


def parse_publish(value: str) -> bool:
    normalized = value.casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    fail("publish must be true or false")


def validate_request(source_ref: str, version: str, publish: bool) -> None:
    if not version or version != version.strip():
        fail("version must be a nonempty value without surrounding whitespace")
    if source_ref.startswith("v"):
        if source_ref[1:] != version:
            fail(f"tag {source_ref} does not match package version {version}")
    elif FULL_COMMIT.fullmatch(source_ref) is None:
        fail("source_ref must be a version tag or a full 40-character commit SHA")
    if publish and source_ref != f"v{version}":
        fail(f"publish=true requires source_ref v{version}")


def git_output(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_source(
    repository: Path,
    source_ref: str,
    version: str,
    github_env: Path | None = None,
) -> str:
    validate_request(source_ref, version, publish=False)
    repository = repository.resolve(strict=True)
    head_commit = git_output(repository, "rev-parse", "HEAD")
    if FULL_COMMIT.fullmatch(head_commit) is None:
        fail(f"git returned an invalid HEAD commit: {head_commit!r}")

    if source_ref.startswith("v"):
        tag_commit = git_output(repository, "rev-list", "-n", "1", f"refs/tags/{source_ref}")
        if tag_commit.casefold() != head_commit.casefold():
            fail(f"checked-out commit does not match tag {source_ref}")
    elif source_ref.casefold() != head_commit.casefold():
        fail("checked-out commit does not match source_ref")

    if github_env is not None:
        with github_env.open("a", encoding="utf-8", newline="\n") as output:
            _ = output.write(f"SOURCE_COMMIT={head_commit.lower()}\n")
    return head_commit.lower()


def package_pattern(version: str) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(PACKAGE_NAME)}-{re.escape(version)}-h[0-9a-f]+_\d+\.conda$"
    )


def package_set(package_root: Path, version: str) -> dict[str, Path]:
    package_root = package_root.resolve(strict=True)
    pattern = package_pattern(version)
    packages: dict[str, Path] = {}

    for subdir in EXPECTED_SUBDIRS:
        directory = package_root / subdir
        if not directory.is_dir():
            fail(f"missing package subdir: {subdir}")
        candidates = sorted(directory.glob(f"{PACKAGE_NAME}-*.conda"))
        if len(candidates) != 1:
            fail(
                f"expected exactly one {PACKAGE_NAME} package for {subdir}, "
                + f"found {len(candidates)}"
            )
        package = candidates[0]
        if package.is_symlink() or not package.is_file():
            fail(f"package must be a regular non-symlink file: {package}")
        if pattern.fullmatch(package.name) is None:
            fail(f"unexpected package filename for {subdir}: {package.name}")
        packages[subdir] = package.resolve()

    discovered = {
        path.resolve()
        for path in package_root.rglob(f"{PACKAGE_NAME}-*.conda")
        if path.is_file()
    }
    if discovered != set(packages.values()):
        fail("package root contains an unexpected sail-jib-json package inventory")
    return packages


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            _ = digest.update(chunk)
    return digest.hexdigest()


def publish_packages(package_root: Path, channel_root: Path, version: str) -> None:
    packages = package_set(package_root, version)
    channel_root = channel_root.resolve(strict=True)
    if not (channel_root / "noarch" / "repodata.json").is_file():
        fail("channel root is not initialized: missing noarch/repodata.json")
    to_publish: list[Path] = []

    for subdir, package in packages.items():
        existing = channel_root / subdir / package.name
        if existing.exists():
            if existing.is_symlink() or not existing.is_file():
                fail(f"existing channel entry is not a regular file: {existing}")
            if sha256(package) == sha256(existing):
                print(f"Channel already contains identical package {subdir}/{package.name}.")
                continue
            fail(
                f"refusing to replace existing package {subdir}/{package.name} "
                + "with different content"
            )
        to_publish.append(package)

    if to_publish:
        _ = subprocess.run(
            [
                "rattler-build",
                "publish",
                *(str(package) for package in to_publish),
                "--to",
                channel_root.as_uri(),
            ],
            check=True,
        )
    else:
        print("Channel already contains the identical package set.")

    for subdir, package in packages.items():
        published = channel_root / subdir / package.name
        if not published.is_file() or sha256(published) != sha256(package):
            fail(f"published package verification failed: {subdir}/{package.name}")
        if not (channel_root / subdir / "repodata.json").is_file():
            fail(f"channel index was not generated for {subdir}")


def commit_channel(channel_root: Path, version: str, source_commit: str) -> None:
    if FULL_COMMIT.fullmatch(source_commit) is None:
        fail("source_commit must be a full 40-character commit SHA")
    channel_root = channel_root.resolve(strict=True)
    paths = [*EXPECTED_SUBDIRS]
    if (channel_root / "noarch").exists():
        paths.append("noarch")

    _ = subprocess.run(
        ["git", "config", "user.name", "github-actions[bot]"],
        cwd=channel_root,
        check=True,
    )
    _ = subprocess.run(
        [
            "git",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ],
        cwd=channel_root,
        check=True,
    )
    _ = subprocess.run(["git", "add", "--", *paths], cwd=channel_root, check=True)
    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=channel_root, check=False
    ).returncode
    if changed == 0:
        print("Channel already contains this package set.")
        return
    if changed != 1:
        fail(f"git diff --cached --quiet failed with exit code {changed}")

    message = f"Publish {PACKAGE_NAME} {version} ({source_commit[:12].lower()})"
    _ = subprocess.run(["git", "commit", "-m", message], cwd=channel_root, check=True)
    _ = subprocess.run(["git", "push"], cwd=channel_root, check=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)

    request = commands.add_parser("validate-request")
    request.add_argument("--source-ref", required=True)
    request.add_argument("--version", required=True)
    request.add_argument("--publish", required=True)

    source = commands.add_parser("validate-source")
    source.add_argument("--repository", required=True, type=Path)
    source.add_argument("--source-ref", required=True)
    source.add_argument("--version", required=True)
    source.add_argument("--github-env", type=Path)

    verify = commands.add_parser("verify-packages")
    verify.add_argument("--package-root", required=True, type=Path)
    verify.add_argument("--version", required=True)

    publish = commands.add_parser("publish-packages")
    publish.add_argument("--package-root", required=True, type=Path)
    publish.add_argument("--channel-root", required=True, type=Path)
    publish.add_argument("--version", required=True)

    commit = commands.add_parser("commit-channel")
    commit.add_argument("--channel-root", required=True, type=Path)
    commit.add_argument("--version", required=True)
    commit.add_argument("--source-commit", required=True)
    return result


def main(arguments: Sequence[str] | None = None) -> int:
    parsed = parser().parse_args(arguments)
    try:
        if parsed.command == "validate-request":
            validate_request(
                parsed.source_ref,
                parsed.version,
                parse_publish(parsed.publish),
            )
        elif parsed.command == "validate-source":
            commit = validate_source(
                parsed.repository,
                parsed.source_ref,
                parsed.version,
                parsed.github_env,
            )
            print(commit)
        elif parsed.command == "verify-packages":
            packages = package_set(parsed.package_root, parsed.version)
            for subdir, package in packages.items():
                print(f"{subdir}: {package.name}")
        elif parsed.command == "publish-packages":
            publish_packages(parsed.package_root, parsed.channel_root, parsed.version)
        elif parsed.command == "commit-channel":
            commit_channel(
                parsed.channel_root,
                parsed.version,
                parsed.source_commit,
            )
        else:
            fail(f"unsupported command: {parsed.command}")
    except (OSError, ReleaseError, subprocess.CalledProcessError) as error:
        parser().error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
