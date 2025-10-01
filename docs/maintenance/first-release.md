# First Release Guide - Step by Step

This guide walks through the complete process of releasing Guage-Kit v0.1.0 to PyPI for the first time.

## 🎯 Prerequisites Checklist

Before starting the first release, ensure:

- [ ] Repository is ready on GitHub
- [ ] All code is tested and working
- [ ] Documentation is complete
- [ ] PyPI account is created
- [ ] GitHub repository settings are configured

## 📋 Step-by-Step First Release

### Step 1: PyPI Account Setup

1. **Create PyPI Account**:
   ```bash
   # Go to https://pypi.org/account/register/
   # Enable 2FA (required)
   ```

2. **Test PyPI Setup** (Optional but recommended):
   ```bash
   # Test on Test PyPI first
   uv build
   twine upload --repository testpypi dist/*
   ```

### Step 2: GitHub Repository Configuration

1. **Enable GitHub Pages**:
   - Repository → Settings → Pages
   - Source: "GitHub Actions"
   - Save settings

2. **Create PyPI Environment**:
   - Repository → Settings → Environments
   - New environment: `pypi`
   - Add protection rules if desired

3. **Configure Trusted Publishing on PyPI**:
   - Go to [PyPI Trusted Publishing](https://pypi.org/manage/account/publishing/)
   - Add new trusted publisher:
     - **PyPI Project Name**: `guage-kit`
     - **Owner**: `abhikanap`
     - **Repository name**: `Guage-Kit`
     - **Workflow filename**: `release.yml`
     - **Environment name**: `pypi`

### Step 3: Pre-release Validation

```bash
# 1. Clone repository
git clone https://github.com/abhikanap/Guage-Kit.git
cd Guage-Kit

# 2. Verify everything works
uv sync --all-extras
uv run pytest tests/test_basic.py -v
uv build
uv run sphinx-build docs docs/_build/html

# 3. Test package installation
pip install dist/guage_kit-*.whl
python -c "import guage_kit; print(guage_kit.__version__)"
```

### Step 4: Create the First Release

```bash
# Option A: Using the bump script (recommended)
./scripts/bump_version.sh patch --dry-run  # Review first
./scripts/bump_version.sh patch           # Create release

# Option B: Manual release
python scripts/release.py --version 0.1.0 --dry-run  # Review
python scripts/release.py --version 0.1.0            # Create

# The script will show you commands like:
# git push origin main
# git push origin v0.1.0
```

### Step 5: Push and Monitor

```bash
# 1. Push the changes and tag
git push origin main
git push origin v0.1.0

# 2. Monitor GitHub Actions
# Go to: https://github.com/abhikanap/Guage-Kit/actions
# Watch for:
# - CI workflow (should pass)
# - Release workflow (should complete)
# - Documentation workflow (should deploy)
```

### Step 6: Verify Release Success

```bash
# 1. Check PyPI
# Visit: https://pypi.org/project/guage-kit/

# 2. Test installation from PyPI
pip install guage-kit==0.1.0

# 3. Verify functionality
python -c "import guage_kit; print(f'✅ Version: {guage_kit.__version__}')"
guage-kit --help

# 4. Check documentation
# Visit: https://abhikanap.github.io/Guage-Kit/

# 5. Verify GitHub release
# Visit: https://github.com/abhikanap/Guage-Kit/releases
```

## 🎉 Success Indicators

After a successful first release, you should see:

- ✅ **PyPI Package**: https://pypi.org/project/guage-kit/
- ✅ **GitHub Release**: https://github.com/abhikanap/Guage-Kit/releases/tag/v0.1.0
- ✅ **Documentation**: https://abhikanap.github.io/Guage-Kit/
- ✅ **Installation Works**: `pip install guage-kit`
- ✅ **CLI Works**: `guage-kit --help`
- ✅ **API Works**: `import guage_kit`

## 🚨 Troubleshooting First Release

### Common Issues and Solutions

1. **PyPI Trusted Publishing Fails**:
   ```bash
   # Check configuration matches exactly:
   # - Repository name: "Guage-Kit" (case sensitive)
   # - Workflow filename: "release.yml"
   # - Environment name: "pypi"
   ```

2. **Package Name Already Exists**:
   ```bash
   # If name is taken, update pyproject.toml:
   name = "guage-kit-yourname"  # Use unique name
   ```

3. **Build Fails**:
   ```bash
   # Test locally first
   uv build
   # Fix any issues before pushing tag
   ```

4. **Documentation Not Deploying**:
   ```bash
   # Check GitHub Pages settings
   # Ensure "GitHub Actions" is selected as source
   # Monitor docs workflow in Actions tab
   ```

5. **Version Tag Issues**:
   ```bash
   # Delete and recreate tag if needed
   git tag -d v0.1.0
   git push origin :refs/tags/v0.1.0
   # Fix version and create new tag
   ```

## 📞 Getting Help

If you encounter issues during the first release:

1. **Check GitHub Actions Logs**: Detailed error messages
2. **PyPI Status**: https://status.python.org/
3. **GitHub Status**: https://www.githubstatus.com/
4. **Community**: GitHub Discussions or Issues

## 🔄 After First Release

Once the first release is successful:

1. **Update Documentation**: Add any missing sections
2. **Create Issues**: For next features/improvements
3. **Setup Monitoring**: Watch for user feedback
4. **Plan Next Release**: Roadmap for future versions

## 📈 Next Steps

After v0.1.0 is live:

```bash
# Future releases become much simpler:
./scripts/bump_version.sh patch    # For bug fixes
./scripts/bump_version.sh minor    # For new features
./scripts/bump_version.sh major    # For breaking changes
```

The automated system handles everything from the second release onwards! 🚀

---

**Congratulations on your first PyPI package release!** 🎉