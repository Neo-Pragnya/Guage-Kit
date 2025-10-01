#!/usr/bin/env python3
"""
Release script for Guage-Kit.

This script helps manage version updates and releases:
1. Updates version in __init__.py
2. Updates CHANGELOG.md with new version
3. Creates git tag
4. Pushes to trigger PyPI release

Usage:
    python scripts/release.py --version 0.2.0
    python scripts/release.py --version 0.2.0 --dry-run
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def update_version_in_init(version: str, dry_run: bool = False) -> None:
    """Update version in src/guage_kit/__init__.py"""
    init_file = Path("src/guage_kit/__init__.py")
    
    if not init_file.exists():
        print(f"❌ {init_file} not found")
        sys.exit(1)
    
    content = init_file.read_text()
    new_content = re.sub(
        r'__version__ = "[^"]*"',
        f'__version__ = "{version}"',
        content
    )
    
    if content == new_content:
        print(f"❌ Version pattern not found in {init_file}")
        sys.exit(1)
    
    if not dry_run:
        init_file.write_text(new_content)
        print(f"✅ Updated version to {version} in {init_file}")
    else:
        print(f"🔍 Would update version to {version} in {init_file}")


def update_changelog(version: str, dry_run: bool = False) -> None:
    """Update CHANGELOG.md with new version"""
    changelog_file = Path("CHANGELOG.md")
    
    if not changelog_file.exists():
        print(f"❌ {changelog_file} not found")
        sys.exit(1)
    
    content = changelog_file.read_text()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Replace [Unreleased] with the new version
    new_content = content.replace(
        "## [Unreleased]",
        f"## [Unreleased]\n\n## [{version}] - {today}"
    )
    
    if content == new_content:
        print(f"❌ [Unreleased] section not found in {changelog_file}")
        sys.exit(1)
    
    if not dry_run:
        changelog_file.write_text(new_content)
        print(f"✅ Updated {changelog_file} with version {version}")
    else:
        print(f"🔍 Would update {changelog_file} with version {version}")


def create_git_tag(version: str, dry_run: bool = False) -> None:
    """Create and push git tag"""
    tag_name = f"v{version}"
    
    # Check if tag already exists
    result = subprocess.run(
        ["git", "tag", "-l", tag_name],
        capture_output=True,
        text=True
    )
    
    if result.stdout.strip():
        print(f"❌ Tag {tag_name} already exists")
        sys.exit(1)
    
    if not dry_run:
        # Stage changes
        subprocess.run(["git", "add", "src/guage_kit/__init__.py", "CHANGELOG.md"], check=True)
        
        # Commit changes
        subprocess.run([
            "git", "commit", "-m", f"Release version {version}"
        ], check=True)
        
        # Create tag
        subprocess.run([
            "git", "tag", "-a", tag_name, "-m", f"Release version {version}"
        ], check=True)
        
        print(f"✅ Created git tag {tag_name}")
        print(f"📤 To trigger release, run: git push origin main && git push origin {tag_name}")
    else:
        print(f"🔍 Would create git tag {tag_name}")


def main():
    parser = argparse.ArgumentParser(description="Release script for Guage-Kit")
    parser.add_argument("--version", required=True, help="New version number (e.g., 0.2.0)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", args.version):
        print(f"❌ Invalid version format: {args.version}. Use semantic versioning (e.g., 0.2.0)")
        sys.exit(1)
    
    print(f"🚀 Preparing release for version {args.version}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    try:
        update_version_in_init(args.version, args.dry_run)
        update_changelog(args.version, args.dry_run)
        create_git_tag(args.version, args.dry_run)
        
        if not args.dry_run:
            print(f"\n🎉 Release {args.version} prepared successfully!")
            print("📋 Next steps:")
            print(f"   1. git push origin main")
            print(f"   2. git push origin v{args.version}")
            print("   3. Monitor GitHub Actions for PyPI release")
        else:
            print(f"\n✅ Dry run completed successfully for version {args.version}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()