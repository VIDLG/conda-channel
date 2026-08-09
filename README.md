# VIDLG conda channel

Static conda channel for VIDLG packages.

Use with pixi/conda:

```toml
channels = ["https://vidlg.github.io/conda-channel", "conda-forge"]
```

## Publishing `sail-jib-json`

The canonical recipe, pinned Sail submodule, ABI-matched exporter plugin, payload
manifest, and package smoke test are maintained in
[`VIDLG/sail-jib-json`](https://github.com/VIDLG/sail-jib-json). This channel
repository owns the Windows package build and static-channel publication, so
publication uses only this repository's built-in `GITHUB_TOKEN`.

Validate an exact source commit without publishing:

```sh
gh workflow run build-sail-jib-json.yml \
  --repo VIDLG/conda-channel \
  -f source_ref=<full-40-character-commit-sha> \
  -f version=0.1.0 \
  -f publish=false
```

The workflow checks out that immutable commit directly, initializes its pinned
Sail submodule, and builds/tests the native `win-64` package. Linux packages are
not part of the current product baseline and will be added only when explicitly
requested.

Publication is tag-only. After a candidate passes, create the matching source tag
and dispatch:

```sh
gh workflow run build-sail-jib-json.yml \
  --repo VIDLG/conda-channel \
  -f source_ref=v0.1.0 \
  -f version=0.1.0 \
  -f publish=true
```

`publish=true` requires an exact `v<version>` tag. Existing package filenames
may be reused only when their SHA-256 is identical; different bytes are rejected.
Successful publication regenerates the `win-64` static index and commits the
package and index update back to this repository.

Validate the channel-owned workflow structure with:

```sh
pixi run python .github/scripts/sail_jib_json/validate_workflow.py
```

## Publishing `verylogic-nextpnr`

The conda recipe is maintained with the source in
[`VIDLG/verylogic-nextpnr`](https://github.com/VIDLG/verylogic-nextpnr/tree/main/downstream/packaging/conda).
This repository owns package construction and static-channel publication because
its built-in `GITHUB_TOKEN` can update the channel without a cross-repository
personal access token. The formal GitHub Release belongs to
[`VIDLG/verylogic-nextpnr`](https://github.com/VIDLG/verylogic-nextpnr/releases),
not to this artifact channel.

Versions use the upstream release baseline plus a downstream post-release number:
`0.10.0.post1` is the first VIDLG distribution based on upstream `0.10.0`.
The package remains `verylogic-nextpnr`, while its executables retain the
compatible upstream names such as `nextpnr-ice40`; do not install another Conda
package that provides the same executables into the same environment.

Validate workflow structure through the channel's locked Pixi environment:

```sh
pixi install --locked
pixi run python .github/scripts/verylogic_nextpnr/validate_workflow.py
```

Before creating a release tag, validate the exact source commit without
publishing it. The workflow deliberately has no `source_ref` default and
defaults `publish` to false. For a commit-SHA candidate, it checks out `main`
and verifies that its `HEAD` is exactly the requested SHA; if `main` advances,
the candidate safely fails and must be re-run for the new commit. Run this
command from the `verylogic-nextpnr` checkout so `git rev-parse HEAD` resolves
the source commit:

```sh
gh workflow run build-verylogic-nextpnr.yml \
  --repo VIDLG/conda-channel \
  -f source_ref="$(git rev-parse HEAD)" \
  -f version=0.10.0.post1 \
  -f publish=false
```

The 0.10.0.post1 source candidate must provide the direct target-identity and
package-pin Python APIs. The workflow builds the `py313` variant, then runs the source repository's
`conda-test` target against the package. It exercises every runtime target
through the embedded API and runs each distinct chipdb integrity check with
bounded parallelism. A channel-owned smoke independently checks iCE40 LP384/UP5K,
small and large Gowin packages, and Xilinx before publication.

After that candidate succeeds, create and push `v0.10.0.post1`, then publish the
immutable tag:

```sh
gh workflow run build-verylogic-nextpnr.yml \
  --repo VIDLG/conda-channel \
  -f source_ref=v0.10.0.post1 \
  -f version=0.10.0.post1 \
  -f publish=true
```

The workflow rejects mutable branch refs, verifies that a `vX.Y.Z` tag matches
the requested package version, builds and installs the `py313` Windows variant,
and checks that exactly that versioned artifact exists. Expensive chipdb
integrity checks run once per distinct database; target-identity and Python API
smoke tests run against the installed package. It then uploads a short-lived
workflow artifact and, when requested, publishes
the packages under `win-64/`, rebuilds the channel indexes, and commits the
generated package and `repodata.json` back to this repository. An existing
package filename is never overwritten with different content.

After the tagged channel publication succeeds, create the formal source release:

```sh
gh workflow run publish-release.yml \
  --repo VIDLG/verylogic-nextpnr \
  -f version=0.10.0.post1
```

That source-owned workflow verifies the immutable `v0.10.0.post1` tag, waits until the
public channel's `repodata.json` contains exactly one `py313` package variant,
then creates the GitHub Release. It uses only the source
repository's built-in `GITHUB_TOKEN`; no cross-repository publishing secret is
required.

CI caches the locked minimal Pixi packaging environment, pinned recipe source
downloads, conda downloads, and `sccache` compiler results.
IceStorm, Apycula, and Project X-Ray data are pinned Git submodules checked out
with each parallel source build. Output cleanup happens before the recipe
source cache is restored, so the build can actually reuse it. CMake build trees
and final packages are deliberately not cached.
