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
publishing it:

```sh
gh workflow run build-verylogic-nextpnr.yml \
  --repo VIDLG/conda-channel \
  -f source_ref="$(git rev-parse HEAD)" \
  -f version=0.1.1 \
  -f publish=false
```

After that candidate succeeds, create and push `v0.1.1`, then publish the
immutable tag:

```sh
gh workflow run build-verylogic-nextpnr.yml \
  --repo VIDLG/conda-channel \
  -f source_ref=v0.1.1 \
  -f version=0.1.1 \
  -f publish=true
```

The workflow rejects mutable branch refs, verifies that a `vX.Y.Z` tag matches
the requested package version, builds and installs both `py312` and `py313`
Windows variants, uploads a short-lived workflow artifact, publishes them under
`win-64/`, rebuilds the
channel indexes, and commits the generated package and `repodata.json` back to
this repository. An existing package filename is never overwritten with
different content.

CI caches the locked minimal Pixi packaging environment, pinned recipe source
downloads (including IceStorm), conda downloads, and `sccache` compiler
results. CMake build trees and final packages are deliberately not cached.
