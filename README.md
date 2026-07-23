# VIDLG conda channel

Static conda channel for VIDLG packages.

Use with pixi/conda:

```toml
channels = ["https://vidlg.github.io/conda-channel", "conda-forge"]
```

## Publishing `verylogic-nextpnr`

The conda recipe is maintained with the source in
[`VIDLG/verylogic-nextpnr`](https://github.com/VIDLG/verylogic-nextpnr/tree/main/recipe).
This repository owns the publishing workflow because its built-in
`GITHUB_TOKEN` can update the channel without a cross-repository personal
access token.

Before creating a release tag, validate the exact source commit without
publishing it. The workflow deliberately has no `source_ref` default and
defaults `publish` to false: until an immutable 0.1.2 source commit exists, do
not substitute a branch name or a placeholder SHA. Run this command from the
`verylogic-nextpnr` checkout so `git rev-parse HEAD` resolves the source commit:

```sh
gh workflow run build-verylogic-nextpnr.yml \
  --repo VIDLG/conda-channel \
  -f source_ref="$(git rev-parse HEAD)" \
  -f version=0.1.2 \
  -f publish=false
```

The 0.1.2 source candidate must provide the new package-pin Python API. The
channel workflow runs the source repository's `conda-test` target, then installs
each package variant and executes a channel-owned package-pin smoke with all
three packaged architecture configurations: iCE40, Gowin, and Xilinx. It also
verifies the resulting package filenames before uploading anything.

After that candidate succeeds, create and push `v0.1.2`, then publish the
immutable tag:

```sh
gh workflow run build-verylogic-nextpnr.yml \
  --repo VIDLG/conda-channel \
  -f source_ref=v0.1.2 \
  -f version=0.1.2 \
  -f publish=true
```

The workflow rejects mutable branch refs, verifies that a `vX.Y.Z` tag matches
the requested package version, builds and installs both `py312` and `py313`
Windows variants, and checks that exactly those two versioned artifacts exist.
It then uploads a short-lived workflow artifact and, when requested, publishes
the packages under `win-64/`, rebuilds the channel indexes, and commits the
generated package and `repodata.json` back to this repository. An existing
package filename is never overwritten with different content.

CI caches the locked minimal Pixi packaging environment, pinned recipe source
downloads, conda downloads, and `sccache` compiler results. IceStorm, Apycula,
and Project X-Ray data are pinned Git submodules checked out with the source.
Output cleanup happens before the recipe source cache is restored, so the build
can actually reuse it. CMake build trees and final packages are deliberately
not cached.
