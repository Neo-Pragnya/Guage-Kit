# GitHub Pages Auto-Documentation

This guide explains how the documentation is automatically updated and published to GitHub Pages when new versions are released.

## 🎯 Overview

Guage-Kit uses GitHub Actions to automatically build and deploy documentation to GitHub Pages whenever:

1. **New release is published** (version tags)
2. **Main branch is updated** with documentation changes
3. **Manual trigger** when needed

## 🔄 Automatic Documentation Workflow

### What Gets Updated Automatically

- ✅ **API Documentation**: Sphinx-generated API reference
- ✅ **User Guides**: Markdown documentation from `docs/` folder
- ✅ **Release Notes**: Updated CHANGELOG.md content
- ✅ **Version Information**: Current package version displayed
- ✅ **Examples**: Code examples and tutorials

### Trigger Conditions

1. **On Release**: When version tags (`v*`) are pushed
2. **On Documentation Changes**: When docs files change in main branch
3. **Manual**: Via GitHub Actions dispatch

## 📚 Documentation Structure

```
docs/
├── index.md                  # Main documentation page
├── api/                      # Auto-generated API docs
│   └── index.rst
├── guides/                   # User guides
│   ├── quickstart.md
│   ├── installation.md
│   └── examples.md
├── references/               # Reference materials
│   └── metrics.rst
├── maintenance/              # Maintainer documentation
│   ├── pypi-publishing.md
│   └── github-pages.md
└── _build/                   # Generated HTML (auto-created)
```

## 🔧 GitHub Pages Configuration

### Repository Settings

1. **GitHub Pages Source**: GitHub Actions
2. **Branch**: Not applicable (Actions deployment)
3. **Path**: Docs are built from `docs/` folder
4. **Domain**: `https://abhikanap.github.io/Guage-Kit/`

### Workflow Configuration

The documentation is built and deployed via `.github/workflows/docs.yml`:

```yaml
name: Documentation

on:
  push:
    branches: [main]
    tags: ['v*']
    paths:
      - 'docs/**'
      - 'src/**'
      - 'pyproject.toml'
  workflow_dispatch:

jobs:
  docs:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write
    
    steps:
      - name: Build documentation
        run: uv run sphinx-build docs docs/_build/html
      
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
        with:
          artifact_name: github-pages
```

## 🚀 Manual Documentation Updates

### For Maintainers

```bash
# 1. Update documentation files
cd docs
# Edit .md or .rst files

# 2. Test locally
uv run sphinx-build . _build/html
# Open _build/html/index.html in browser

# 3. Commit and push
git add docs/
git commit -m "Update documentation"
git push origin main

# 4. GitHub Actions will automatically deploy
```

### For Contributors

```bash
# 1. Fork repository and create branch
git checkout -b docs/improve-guides

# 2. Make documentation changes
# Edit files in docs/ folder

# 3. Test locally
uv sync --extra docs
uv run sphinx-build docs docs/_build/html

# 4. Create Pull Request
# Documentation will be deployed when PR is merged
```

## 📝 Documentation Best Practices

### Writing Documentation

1. **Use Clear Headings**: Proper hierarchy with #, ##, ###
2. **Code Examples**: Include working code snippets
3. **Cross-References**: Link between documentation sections
4. **Version Information**: Mention version-specific features

### File Organization

- **Guides**: Step-by-step instructions in `docs/guides/`
- **API Reference**: Auto-generated in `docs/api/`
- **Examples**: Working examples in `docs/examples/`
- **Maintenance**: Internal docs in `docs/maintenance/`

### Markdown vs reStructuredText

- **Markdown (.md)**: User-facing guides, README-style content
- **reStructuredText (.rst)**: API documentation, Sphinx-specific features

## 🔍 Monitoring Documentation Builds

### Success Indicators

- ✅ GitHub Actions workflow completes successfully
- ✅ Documentation site updates at `https://abhikanap.github.io/Guage-Kit/`
- ✅ Version number matches latest release
- ✅ New content appears correctly

### Verification Steps

```bash
# 1. Check GitHub Actions
# Go to Actions → Documentation workflow

# 2. Verify deployment
# Visit: https://abhikanap.github.io/Guage-Kit/

# 3. Test local build
uv run sphinx-build docs docs/_build/html
```

## 🚨 Troubleshooting Documentation

### Common Issues

1. **Build Failures**:
   - Check Sphinx syntax errors
   - Verify file references exist
   - Test locally first

2. **Missing Pages**:
   - Ensure files are in correct directories
   - Check `toctree` directives in index files
   - Verify file extensions (.md vs .rst)

3. **Deployment Issues**:
   - Check GitHub Pages settings
   - Verify Actions permissions
   - Monitor workflow logs

### Fixing Documentation Issues

```bash
# 1. Test build locally
uv run sphinx-build docs docs/_build/html -W

# 2. Check for warnings and errors
# Fix any syntax issues

# 3. Commit fixes
git add docs/
git commit -m "Fix documentation build issues"
git push origin main
```

## 📊 Documentation Metrics

### Tracking Usage

- **GitHub Pages Analytics**: Built-in traffic statistics
- **GitHub Insights**: Documentation file views
- **Issue Tracking**: Documentation-related issues

### Quality Measures

- ✅ **Build Success Rate**: All builds should succeed
- ✅ **Coverage**: All public APIs documented
- ✅ **Freshness**: Updated with each release
- ✅ **Accessibility**: Clear navigation and structure

## 🔄 Integration with Releases

### Automatic Updates on Release

When a new version is released:

1. **Version Badge**: Updates to show latest version
2. **API Changes**: New features automatically documented
3. **Release Notes**: CHANGELOG.md content integrated
4. **Installation Instructions**: Updated with correct version

### Manual Updates for Major Releases

For significant updates:

1. **Update Examples**: Ensure code examples work with new version
2. **Migration Guides**: Add upgrade instructions if needed
3. **Breaking Changes**: Document API changes clearly
4. **New Features**: Add comprehensive guides for new functionality

This automated system ensures your documentation is always current and accessible! 📖