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

Publish an immutable source tag or full commit SHA:

```sh
gh workflow run build-verylogic-nextpnr.yml \
  --repo VIDLG/conda-channel \
  -f source_ref=v0.1.0 \
  -f version=0.1.0
```

The workflow builds and tests the Windows package, publishes it under
`win-64/`, rebuilds the channel indexes, and commits the generated package and
`repodata.json` back to this repository.
