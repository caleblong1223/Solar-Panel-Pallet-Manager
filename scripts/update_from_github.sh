#!/bin/bash
# Update from GitHub script for Pallet Manager
# Pulls latest changes and automatically rebuilds the application

set -e

echo "========================================"
echo "Pallet Manager - Update from GitHub"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if git is available
if ! command -v git >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: Git is not installed or not in PATH${NC}"
    echo "Please install Git and try again."
    exit 1
fi

# Check if this is a git repository
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: This is not a Git repository${NC}"
    echo "Please initialize the repository or clone from GitHub first."
    echo ""
    echo "To clone from GitHub:"
    echo "  git clone <your-github-repo-url>"
    echo "  cd <repository-directory>"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${BLUE}📍 Current branch: ${CURRENT_BRANCH}${NC}"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
    echo "Your local changes will be preserved, but you may need to resolve conflicts."
    echo ""
    read -p "Continue anyway? (y/N): " continue_anyway
    if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
        echo "Update cancelled."
        exit 0
    fi
    echo ""
fi

# Fetch latest changes
echo -e "${BLUE}🔄 Fetching latest changes from remote...${NC}"
if ! git fetch origin; then
    echo -e "${RED}❌ Failed to fetch from remote${NC}"
    exit 1
fi

# Check if we're behind remote
BEHIND_COUNT=$(git rev-list HEAD...origin/${CURRENT_BRANCH} --count 2>/dev/null || echo "0")
if [ "$BEHIND_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ Your branch is already up to date!${NC}"
    echo ""
    read -p "Rebuild anyway? (y/N): " rebuild_anyway
    if [[ ! "$rebuild_anyway" =~ ^[Yy]$ ]]; then
        echo "No update needed."
        exit 0
    fi
else
    echo -e "${BLUE}📦 ${BEHIND_COUNT} new commits available${NC}"
    echo ""
fi

# Pull changes
echo -e "${BLUE}⬇️  Pulling latest changes...${NC}"
if ! git pull origin ${CURRENT_BRANCH}; then
    echo -e "${RED}❌ Failed to pull changes${NC}"
    echo ""
    echo "This might be due to merge conflicts. Please resolve them manually:"
    echo "  1. Check git status: git status"
    echo "  2. Resolve conflicts in the affected files"
    echo "  3. Commit the resolved changes: git commit"
    exit 1
fi

echo -e "${GREEN}✅ Successfully updated from GitHub!${NC}"
echo ""

# Automatically rebuild the application
echo -e "${BLUE}🔨 Rebuilding application...${NC}"

# Detect platform and run appropriate build script
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected macOS, running full build..."
    if [ -f "./scripts/install_all.sh" ]; then
        ./scripts/install_all.sh
    else
        echo -e "${RED}❌ Build script not found: ./scripts/install_all.sh${NC}"
        exit 1
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "Detected Windows, running full build..."
    if [ -f "./scripts/install_all_windows.bat" ]; then
        ./scripts/install_all_windows.bat
    else
        echo -e "${RED}❌ Build script not found: ./scripts/install_all_windows.bat${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Unknown platform: $OSTYPE${NC}"
    echo "Please run the appropriate build script manually:"
    echo "  macOS: ./scripts/install_all.sh"
    echo "  Windows: scripts\\install_all_windows.bat"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Rebuild complete!${NC}"
echo ""
echo "📦 New installers available in dist/:"
echo "  • macOS: PalletManager-Installer.pkg / PalletManager-Installer.dmg"
echo "  • Windows: Pallet Manager-Setup.exe"

echo ""
echo -e "${GREEN}🎉 Update process complete!${NC}"
echo ""
echo "To run the updated application:"
echo "  From source: python app/pallet_builder_gui.py"
echo "  Built app: See dist/ directory"
