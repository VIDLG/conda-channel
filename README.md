# VIDLG conda channel

Static conda channel for VIDLG packages.

Use with pixi/conda:

```toml
channels = ["https://vidlg.github.io/conda-channel", "conda-forge"]
```

## Publishing `verylogic-nextpnr`

The conda recipe is maintained with the source in
[`VIDLG/verylogic-nextpnr`](https://github.com/VIDLG/verylogic-nextpnr/tree/main/downstream/packaging/conda).
This repository owns package construction and static-channel publication because
its built-in `GITHUB_TOKEN` can update the channel without a cross-repository
personal access token. The formal GitHub Release belongs to
[`VIDLG/verylogic-nextpnr`](https://github.com/VIDLG/verylogic-nextpnr/releases),
not to this artifact channel.

Validate workflow structure through the channel's locked Pixi environment:

```sh
pixi install --locked
pixi run python .github/scripts/validate_verylogic_nextpnr_workflow.py
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
  -f version=0.1.5 \
  -f publish=false
```

The 0.1.5 source candidate must provide the direct target-identity and
package-pin Python APIs. The workflow builds the `py312` and `py313` variants
in parallel, then runs the source repository's `conda-test` target against the
combined artifacts. Both Python ABIs exercise every runtime target through the
embedded API; one ABI additionally runs each distinct chipdb integrity check
with bounded parallelism. A channel-owned smoke independently checks iCE40
LP384/UP5K, small and large Gowin packages, and Xilinx before publication.

After that candidate succeeds, create and push `v0.1.5`, then publish the
immutable tag:

```sh
gh workflow run build-verylogic-nextpnr.yml \
  --repo VIDLG/conda-channel \
  -f source_ref=v0.1.5 \
  -f version=0.1.5 \
  -f publish=true
```

The workflow rejects mutable branch refs, verifies that a `vX.Y.Z` tag matches
the requested package version, builds the `py312` and `py313` Windows variants
in parallel, installs both, and checks that exactly those two versioned
artifacts exist. Expensive chipdb integrity checks run once per distinct
database; target-identity and Python API smoke tests still run against both
Python ABIs. It then uploads a short-lived workflow artifact and, when
requested, publishes
the packages under `win-64/`, rebuilds the channel indexes, and commits the
generated package and `repodata.json` back to this repository. An existing
package filename is never overwritten with different content.

After the tagged channel publication succeeds, create the formal source release:

```sh
gh workflow run publish-release.yml \
  --repo VIDLG/verylogic-nextpnr \
  -f version=0.1.5
```

That source-owned workflow verifies the immutable `v0.1.5` tag, waits until the
public channel's `repodata.json` contains exactly one `py312` and one `py313`
package variant, then creates the GitHub Release. It uses only the source
repository's built-in `GITHUB_TOKEN`; no cross-repository publishing secret is
required.

CI caches the locked minimal Pixi packaging environment, pinned recipe source
downloads, conda downloads, and per-Python-ABI `sccache` compiler results.
IceStorm, Apycula, and Project X-Ray data are pinned Git submodules checked out
with each parallel source build. Output cleanup happens before the recipe
source cache is restored, so the build can actually reuse it. CMake build trees
and final packages are deliberately not cached.
