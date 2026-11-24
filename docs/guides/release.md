---
title: Releasing
description: How a Guage Kit version is verified, built, scanned and published to PyPI (for maintainers).
---

# Releasing

## Gates a release must pass

| Gate | Command | Blocks on |
| --- | --- | --- |
| Quality | `make verify` | lint, format, strict mypy, unit tests, a copyleft runtime licence, a stale metric catalogue |
| Acceptance | `make acceptance-wheel` | a BLOCK decision: a blocker capability failing, or without a scenario |
| Distribution scan | `make scan` | secrets, vulnerable dependencies, unreviewed malicious-code heuristics in the wheel or sdist |
| Metadata | `make build-check` | invalid package metadata |

## Steps

1. Update `src/guage_kit/version.py` and move the *Unreleased* notes in `CHANGELOG.md` under the new version.
2. Run the four gates above.
3. Publish to TestPyPI first, install from there in a clean environment, then publish to PyPI:

   ```bash
   make publish-testpypi
   uv venv /tmp/gk && uv pip install --python /tmp/gk/bin/python \
     --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ guage-kit==X.Y.Z
   /tmp/gk/bin/guage demo -o /tmp/gk-demo
   make publish-pypi
   ```

   The tokens come from `.env` (`UV_PUBLISH_TOKEN`, `UV_PUBLISH_TOKEN_TESTPYPI`), which is git-ignored.

4. Tag the release (`vX.Y.Z`) and push the tag. The `release-pypi` workflow builds once, runs the acceptance gate on
   that exact wheel, scans it, attests provenance and publishes with OIDC trusted publishing. If the version is
   already on PyPI (published by hand in step 3), it skips the upload and only creates the GitHub release.

> [!WARNING]
> Never re-upload a version. If something is wrong after publishing, release the next patch version.

## Trusted publishing

On PyPI, add a trusted publisher for `Neo-Pragnya/Guage-Kit`, workflow `release-pypi.yml`, environment `pypi`
(and the same on TestPyPI with `release-testpypi.yml`, environment `testpypi`). Until then the workflows fall back to
the `UV_PUBLISH_TOKEN` repository secret.

## Website

The `docs-site` workflow builds `website/` (Astro) with the live demo reports and deploys it to GitHub Pages on every
push to `main`. In the repository settings, set **Pages → Source: GitHub Actions** once.
