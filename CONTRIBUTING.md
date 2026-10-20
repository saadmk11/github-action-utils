# Contributing

Use Python 3.15 and uv 0.13.1 for development. The package supports Python
3.11–3.15 and has no runtime dependencies.

## Development

```sh
uv sync --locked
uv run --locked ruff format .
uv run --locked tox run -e lint,type,coverage,package
uv run --locked tox run -e py311,py312,py313,py314,py315
```

Select installed Python versions locally; CI runs all supported versions on
Linux, Windows, and macOS. Tox tests an installed wheel. Settings are in
`pyproject.toml`; `uv.lock` pins development dependencies.

Test observable behavior and add regression tests for bug fixes. Package code
requires 100% statement and branch coverage. Source, tests, and scripts must pass
strict mypy. Check workflow changes with actionlint 1.7.12.

The `package` check verifies source and wheel installs, installed typing, and
upgrades from the published 1.1.0 package. It needs network access. To use a local
1.1.0 wheel, run `python scripts/check_distribution.py --previous-wheel /path/to/wheel`
after building the distributions.

## GitHub Actions integration

The [feature showcase](.github/workflows/showcase.yaml) checks cross-step values,
PATH, and main/post action state on all three operating systems. Node.js launches
the state-test hooks. Inspect annotations, groups, masking, matchers, debug
output, post-hook logs, and the job summary. `MANUAL` needs visual inspection;
`SKIP` means the runner lacks the required feature.

## Releases

1. Update `pyproject.toml` and `CHANGELOG.md`, then run `uv lock` and the checks
   above. Inspect the hosted showcase.
2. Configure the PyPI Trusted Publisher for `saadmk11/github-action-utils`,
   workflow `pypi_publish.yaml`, and the protected `pypi` environment.
3. Publish a GitHub release with a matching tag, such as `v2.0.0`. For a manual
   workflow run, select that tag. The workflow checks the tag, commit, release,
   and package version; validates the distributions; publishes them with uv
   Trusted Publishing; and checks the installed PyPI version.

## Reporting issues

Include the Python and package versions, a minimal example, relevant workflow
steps, and expected versus actual behavior. Remove secrets from logs and examples.
