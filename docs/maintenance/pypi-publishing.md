# PyPI Publishing Guide for Guage-Kit

This guide explains how to publish Guage-Kit to PyPI, whether you're a maintainer or contributing from a fork.

## 🎯 Overview

Guage-Kit uses an automated release system with two main approaches:

1. **For Maintainers**: Direct releases from main repository
2. **For Contributors**: Fork-based contributions with maintainer approval

## 👥 For Project Maintainers

### Initial Setup (One-time)

#### 1. PyPI Trusted Publishing Setup

1. **Create PyPI Account**:
   - Go to [PyPI.org](https://pypi.org) and create an account
   - Enable 2FA (required for publishing)

2. **Register Project Name**:
   ```bash
   # First, create a test upload to reserve the name
   uv build
   twine upload --repository testpypi dist/*
   ```

3. **Configure Trusted Publishing**:
   - Go to [PyPI Trusted Publishing](https://pypi.org/manage/account/publishing/)
   - Click "Add a new trusted publisher"
   - Fill in:
     - **PyPI Project Name**: `guage-kit`
     - **Owner**: `abhikanap`
     - **Repository name**: `Guage-Kit`
     - **Workflow filename**: `release.yml`
     - **Environment name**: `pypi`

#### 2. GitHub Repository Setup

1. **Create GitHub Environment**:
   - Go to Repository → Settings → Environments
   - Create environment: `pypi`
   - Add protection rules:
     - ✅ Required reviewers (optional)
     - ✅ Restrict to protected branches

2. **Enable GitHub Pages**:
   - Go to Repository → Settings → Pages
   - Source: GitHub Actions
   - This allows docs to be auto-published

### Publishing a Release

#### Method 1: Automatic Version Bump (Recommended)

```bash
# 1. Clone/update repository
git clone https://github.com/abhikanap/Guage-Kit.git
cd Guage-Kit
git checkout main
git pull origin main

# 2. Create release (choose one)
./scripts/bump_version.sh patch    # Bug fixes (0.1.0 → 0.1.1)
./scripts/bump_version.sh minor    # New features (0.1.0 → 0.2.0)
./scripts/bump_version.sh major    # Breaking changes (0.1.0 → 1.0.0)

# 3. Follow the prompts and push when ready
# The script will show you the exact commands to run
```

#### Method 2: Manual Version Control

```bash
# 1. Prepare release
python scripts/release.py --version 0.2.0

# 2. Review changes
git diff
git status

# 3. Push to trigger release
git push origin main
git push origin v0.2.0

# 4. Monitor GitHub Actions
# Go to Actions tab and watch the release workflow
```

#### Method 3: GitHub Web Interface

1. **Create Release via GitHub**:
   - Go to Releases → "Create a new release"
   - Tag: `v0.2.0` (must start with 'v')
   - Title: `Release 0.2.0`
   - Description: Add release notes
   - Click "Publish release"

2. **Note**: This bypasses version file updates, so update manually first

### What Happens During Release

1. **GitHub Actions Triggered**: Tag push starts the workflow
2. **Build Process**: Package is built and tested
3. **PyPI Publishing**: Automatic upload via trusted publishing
4. **GitHub Release**: Created with signed artifacts
5. **Documentation**: GitHub Pages updated automatically

## 🍴 For Contributors (Fork-based)

### Contributing Changes

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/Guage-Kit.git
cd Guage-Kit

# 3. Create feature branch
git checkout -b feature/your-feature

# 4. Make changes and test
uv sync --all-extras
uv run pytest
uv build

# 5. Commit and push
git add .
git commit -m "Add your feature"
git push origin feature/your-feature

# 6. Create Pull Request
# Go to GitHub and create PR to main repository
```

### Version Updates in Forks

**Important**: Contributors should NOT update versions in PRs. Version bumps are handled by maintainers during release.

```bash
# ❌ DON'T do this in PRs:
# - Modify src/guage_kit/__init__.py version
# - Update CHANGELOG.md with version numbers
# - Create git tags

# ✅ DO this instead:
# - Add entries to CHANGELOG.md under "[Unreleased]"
# - Focus on your feature/bug fix
# - Let maintainers handle versioning
```

### Testing Fork Changes

```bash
# Test your changes locally
uv build
pip install dist/guage_kit-*.whl

# Test CLI
guage-kit --help

# Test API
python -c "import guage_kit; print(guage_kit.__version__)"
```

## 🚨 Emergency Procedures

### Rollback a Release

```bash
# 1. Yank from PyPI (if critical issue)
twine yank guage-kit==0.2.0 --reason "Critical bug fix needed"

# 2. Delete GitHub release
# Go to Releases → Delete release

# 3. Delete git tag
git tag -d v0.2.0
git push origin :refs/tags/v0.2.0

# 4. Create hotfix release
./scripts/bump_version.sh patch
```

### Fix Failed Release

```bash
# 1. Check GitHub Actions logs
# Go to Actions → Failed workflow → View logs

# 2. Common fixes:
# - Version format issues
# - PyPI trusted publishing config
# - Missing dependencies

# 3. Delete failed tag and retry
git tag -d v0.2.0
git push origin :refs/tags/v0.2.0
# Fix issue and create new tag
```

## 📊 Monitoring Releases

### Success Indicators

- ✅ GitHub Actions workflow completes successfully
- ✅ Package appears on [PyPI](https://pypi.org/project/guage-kit/)
- ✅ GitHub Release created with artifacts
- ✅ Documentation updated on GitHub Pages

### Verification Commands

```bash
# Test installation from PyPI
pip install guage-kit==0.2.0

# Verify version
python -c "import guage_kit; print(guage_kit.__version__)"

# Test basic functionality
echo '{"query": {"id": "q1", "prompt": "test"}, "generation": {"query_id": "q1", "text": "response", "model": "test"}}' > test.jsonl
guage-kit run --data test.jsonl --metrics rougeL
```

## 🔧 Troubleshooting

### Common Issues

1. **"Package already exists" on PyPI**:
   - Can't re-upload same version
   - Bump version number and retry

2. **Trusted publishing fails**:
   - Verify PyPI configuration
   - Check GitHub environment settings
   - Ensure workflow file matches PyPI config

3. **Build failures**:
   - Check dependencies in pyproject.toml
   - Verify Python version compatibility
   - Test locally with `uv build`

4. **Permission denied**:
   - Only maintainers can push to main branch
   - Contributors must use Pull Requests

### Getting Help

- **GitHub Issues**: Report problems
- **GitHub Discussions**: Ask questions
- **Actions Logs**: Detailed error information
- **PyPI Help**: [PyPI Support](https://pypi.org/help/)

## 📋 Checklist for Maintainers

### Before First Release
- [ ] PyPI account created with 2FA
- [ ] Trusted publishing configured
- [ ] GitHub environment `pypi` created
- [ ] GitHub Pages enabled
- [ ] Test build works: `uv build`
- [ ] All tests pass: `uv run pytest`

### For Each Release
- [ ] All PRs merged and reviewed
- [ ] Tests passing on main branch
- [ ] CHANGELOG.md updated
- [ ] Version bump appropriate (patch/minor/major)
- [ ] Release notes prepared
- [ ] Post-release verification completed

### Security Considerations

- ✅ No API tokens stored in repository
- ✅ Trusted publishing for secure authentication
- ✅ Signed artifacts with Sigstore
- ✅ Protected branches and environments
- ✅ 2FA required for PyPI access

This system ensures secure, automated, and reliable package publishing! 🚀