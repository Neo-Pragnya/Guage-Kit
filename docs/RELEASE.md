# Release Process for Guage-Kit

This document outlines the automated release process for publishing Guage-Kit to PyPI.

## Overview

The release process is fully automated using GitHub Actions and triggered by version tags. Here's how it works:

1. **Version Management**: Version is stored in `src/guage_kit/__init__.py`
2. **Tag-based Releases**: Pushing a git tag starting with `v` triggers the release
3. **Automated Publishing**: GitHub Actions builds and publishes to PyPI
4. **GitHub Releases**: Automatically creates GitHub releases with signed artifacts

## Quick Release

### Option 1: Using the Helper Script (Recommended)

```bash
# Patch release (0.1.0 -> 0.1.1)
./scripts/bump_version.sh patch

# Minor release (0.1.0 -> 0.2.0)
./scripts/bump_version.sh minor

# Major release (0.1.0 -> 1.0.0)
./scripts/bump_version.sh major

# Dry run to see what would happen
./scripts/bump_version.sh minor --dry-run
```

### Option 2: Manual Release

```bash
# 1. Update version manually
python scripts/release.py --version 0.2.0

# 2. Push changes and tag
git push origin main
git push origin v0.2.0
```

## Release Workflow Details

### 1. Version Management

The version is stored in a single place:
- **Source**: `src/guage_kit/__init__.py` (`__version__ = "0.1.0"`)
- **Build**: `pyproject.toml` uses dynamic versioning via hatchling

### 2. Release Triggers

Releases are triggered by pushing git tags:
```bash
git tag v0.2.0
git push origin v0.2.0
```

### 3. GitHub Actions Workflow

The release workflow (`.github/workflows/release.yml`) includes:

1. **Build**: Creates wheel and source distribution
2. **PyPI Publishing**: Uses trusted publishing (no API tokens needed)
3. **GitHub Release**: Creates release with signed artifacts
4. **Artifact Signing**: Uses Sigstore for supply chain security

### 4. PyPI Publishing

- **Method**: Trusted publishing via OIDC (no API tokens required)
- **Trigger**: Only on version tags (`v*`)
- **Security**: Artifacts are signed with Sigstore

## Setup Requirements

### 1. GitHub Repository Settings

Configure trusted publishing on PyPI:

1. Go to [PyPI Trusted Publishing](https://pypi.org/manage/account/publishing/)
2. Add a new trusted publisher:
   - **PyPI Project Name**: `guage-kit`
   - **Owner**: `abhikanap`
   - **Repository name**: `Guage-Kit`
   - **Workflow filename**: `release.yml`
   - **Environment name**: `pypi`

### 2. GitHub Environment

Create a GitHub environment named `pypi`:

1. Go to Repository → Settings → Environments
2. Create new environment: `pypi`
3. Add protection rules if needed

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes (1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (1.0.0 → 1.0.1)

## Testing Releases

### Test PyPI (Optional)

To test releases on Test PyPI:

```bash
# Build package
uv build

# Upload to Test PyPI (requires test.pypi.org account)
twine upload --repository testpypi dist/*

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ guage-kit
```

### Local Testing

```bash
# Build and test locally
uv build
pip install dist/guage_kit-*.whl

# Verify installation
python -c "import guage_kit; print(guage_kit.__version__)"
```

## Rollback Process

If a release needs to be rolled back:

1. **PyPI**: Cannot delete releases, but can yank them
2. **GitHub**: Delete the release and tag
3. **Fix**: Create a new patch release with fixes

```bash
# Yank a release on PyPI (if needed)
twine yank guage-kit==0.2.0 --reason "Reason for yanking"
```

## Monitoring

Monitor releases through:

- **GitHub Actions**: Watch workflow runs
- **PyPI**: Check package page for new versions
- **GitHub Releases**: Verify artifacts are published

## Troubleshooting

### Common Issues

1. **Tag already exists**: Delete and recreate tag
   ```bash
   git tag -d v0.2.0
   git push origin :refs/tags/v0.2.0
   ```

2. **Version mismatch**: Ensure version in `__init__.py` matches tag

3. **Trusted publishing fails**: Verify PyPI trusted publisher configuration

4. **Build fails**: Check dependencies and build requirements

### Getting Help

- Check GitHub Actions logs for detailed error messages
- Verify PyPI trusted publishing configuration
- Ensure all required files are present and properly formatted

## Security Notes

- No API tokens are stored in the repository
- All artifacts are signed with Sigstore
- Trusted publishing uses OIDC for secure authentication
- Supply chain security is maintained through GitHub's security features