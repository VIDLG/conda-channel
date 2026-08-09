from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .release import (
    EXPECTED_SUBDIRS,
    ReleaseError,
    package_set,
    publish_packages,
    validate_request,
)


class RequestValidationTests(unittest.TestCase):
    def test_candidate_commit_and_matching_tag_are_valid(self) -> None:
        validate_request("a" * 40, "0.1.0", publish=False)
        validate_request("v0.1.0", "0.1.0", publish=True)

    def test_publish_requires_matching_tag(self) -> None:
        with self.assertRaisesRegex(ReleaseError, "publish=true requires"):
            validate_request("a" * 40, "0.1.0", publish=True)
        with self.assertRaisesRegex(ReleaseError, "does not match"):
            validate_request("v0.2.0", "0.1.0", publish=False)


class PackageSetTests(unittest.TestCase):
    def make_packages(self, root: Path, version: str = "0.1.0") -> dict[str, Path]:
        packages: dict[str, Path] = {}
        for index, subdir in enumerate(EXPECTED_SUBDIRS, start=1):
            package = root / subdir / f"sail-jib-json-{version}-h{index:08x}_0.conda"
            package.parent.mkdir(parents=True)
            package.write_bytes(f"package-{subdir}".encode())
            packages[subdir] = package.resolve()
        return packages

    def test_requires_exact_windows_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = self.make_packages(root)
            self.assertEqual(package_set(root, "0.1.0"), expected)

            extra = root / "win-64" / "sail-jib-json-0.1.0-hffffffff_0.conda"
            extra.write_bytes(b"extra")
            with self.assertRaisesRegex(ReleaseError, "exactly one"):
                package_set(root, "0.1.0")

    def test_rejects_existing_filename_with_different_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packages = self.make_packages(root / "packages")
            channel = root / "channel"
            (channel / "noarch").mkdir(parents=True)
            (channel / "noarch" / "repodata.json").write_text("{}", encoding="utf-8")
            conflicting = channel / "win-64" / packages["win-64"].name
            conflicting.parent.mkdir()
            conflicting.write_bytes(b"different")

            with patch("sail_jib_json.release.subprocess.run") as run:
                with self.assertRaisesRegex(ReleaseError, "refusing to replace"):
                    publish_packages(root / "packages", channel, "0.1.0")
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
