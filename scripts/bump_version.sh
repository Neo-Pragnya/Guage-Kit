#!/bin/bash

# Version Management and Release Helper Script
# Usage: ./scripts/bump_version.sh [patch|minor|major] [--dry-run]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current version from __init__.py
get_current_version() {
    grep -o '__version__ = "[^"]*"' src/guage_kit/__init__.py | cut -d'"' -f2
}

# Increment version based on type
increment_version() {
    local current_version=$1
    local bump_type=$2
    
    IFS='.' read -r major minor patch <<< "$current_version"
    
    case $bump_type in
        "major")
            echo "$((major + 1)).0.0"
            ;;
        "minor")
            echo "${major}.$((minor + 1)).0"
            ;;
        "patch")
            echo "${major}.${minor}.$((patch + 1))"
            ;;
        *)
            echo "Error: Invalid bump type. Use 'major', 'minor', or 'patch'"
            exit 1
            ;;
    esac
}

# Main script
main() {
    local bump_type=${1:-patch}
    local dry_run=${2}
    
    if [[ ! -f "src/guage_kit/__init__.py" ]]; then
        echo -e "${RED}❌ Error: src/guage_kit/__init__.py not found${NC}"
        exit 1
    fi
    
    local current_version
    current_version=$(get_current_version)
    
    if [[ -z "$current_version" ]]; then
        echo -e "${RED}❌ Error: Could not find current version${NC}"
        exit 1
    fi
    
    local new_version
    new_version=$(increment_version "$current_version" "$bump_type")
    
    echo -e "${BLUE}📦 Guage-Kit Version Management${NC}"
    echo -e "${YELLOW}Current version: ${current_version}${NC}"
    echo -e "${YELLOW}New version:     ${new_version}${NC}"
    echo -e "${YELLOW}Bump type:       ${bump_type}${NC}"
    
    if [[ "$dry_run" == "--dry-run" ]]; then
        echo -e "${BLUE}🔍 DRY RUN MODE${NC}"
        python scripts/release.py --version "$new_version" --dry-run
    else
        echo -e "${YELLOW}⚠️  This will create a new release. Continue? (y/N)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            python scripts/release.py --version "$new_version"
            echo -e "${GREEN}✅ Release preparation completed!${NC}"
        else
            echo -e "${YELLOW}❌ Release cancelled${NC}"
        fi
    fi
}

# Show usage if help requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: $0 [patch|minor|major] [--dry-run]"
    echo ""
    echo "Version bump types:"
    echo "  patch  - Bug fixes (0.1.0 -> 0.1.1)"
    echo "  minor  - New features (0.1.0 -> 0.2.0)"
    echo "  major  - Breaking changes (0.1.0 -> 1.0.0)"
    echo ""
    echo "Options:"
    echo "  --dry-run  Show what would be done without making changes"
    echo ""
    echo "Examples:"
    echo "  $0 patch           # Bump patch version and prepare release"
    echo "  $0 minor --dry-run # Show what a minor version bump would do"
    exit 0
fi

main "$@"