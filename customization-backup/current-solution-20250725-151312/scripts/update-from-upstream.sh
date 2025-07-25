#!/bin/bash
# Update mAI from Open WebUI upstream
# This script automates the process of merging updates while preserving customizations

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
UPSTREAM_REMOTE="upstream"
UPSTREAM_REPO="https://github.com/open-webui/open-webui.git"
MAIN_BRANCH="main"
DEV_BRANCH="customization"
CUSTOMIZATION_FILE="docs/customization/customization-checklist.md"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository!"
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        log_error "Uncommitted changes detected! Please commit or stash them first."
        exit 1
    fi
    
    # Check if upstream remote exists
    if ! git remote | grep -q "^${UPSTREAM_REMOTE}$"; then
        log_warn "Upstream remote not found. Adding it now..."
        git remote add ${UPSTREAM_REMOTE} ${UPSTREAM_REPO}
    fi
    
    # Check if on correct branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "$DEV_BRANCH" ]; then
        log_warn "Not on ${DEV_BRANCH} branch. Switching..."
        git checkout ${DEV_BRANCH}
    fi
}

create_backup() {
    log_info "Creating backup branch..."
    BACKUP_BRANCH="backup-$(date +%Y%m%d-%H%M%S)"
    git checkout -b ${BACKUP_BRANCH}
    git checkout ${DEV_BRANCH}
    log_info "Backup created: ${BACKUP_BRANCH}"
}

fetch_upstream() {
    log_info "Fetching upstream changes..."
    git fetch ${UPSTREAM_REMOTE} --tags
    
    # Get latest version tag
    LATEST_TAG=$(git describe --tags $(git rev-list --tags --max-count=1 ${UPSTREAM_REMOTE}/${MAIN_BRANCH}))
    log_info "Latest upstream version: ${LATEST_TAG}"
    
    # Show current version
    CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "no-tag")
    log_info "Current mAI version: ${CURRENT_VERSION}"
}

merge_upstream() {
    log_info "Merging upstream changes..."
    
    # Try automatic merge
    if git merge ${LATEST_TAG} --no-commit --no-ff; then
        log_info "Automatic merge successful (no conflicts)"
    else
        log_warn "Merge conflicts detected. Manual resolution required."
        
        # Show conflict files
        echo -e "\n${YELLOW}Conflicted files:${NC}"
        git diff --name-only --diff-filter=U
        
        # Provide guidance
        echo -e "\n${YELLOW}Common conflict areas in mAI:${NC}"
        echo "1. package.json - Keep 'name': 'mai'"
        echo "2. src/lib/components/chat/Chat.svelte - Preserve background patterns"
        echo "3. Translation files - Accept upstream, re-add customizations"
        echo "4. Settings components - Preserve custom features"
        
        echo -e "\n${YELLOW}To resolve:${NC}"
        echo "1. Edit conflicted files"
        echo "2. Run: git add <resolved-files>"
        echo "3. Run: ./scripts/update-from-upstream.sh --continue"
        
        exit 1
    fi
}

apply_customizations() {
    log_info "Verifying mAI customizations..."
    
    # Check critical files
    declare -a CRITICAL_FILES=(
        "package.json"
        "src/lib/constants.ts"
        "src/lib/components/chat/Placeholder.svelte"
        "src/lib/components/chat/Chat.svelte"
        "CUSTOMIZATIONS.yaml"
    )
    
    for file in "${CRITICAL_FILES[@]}"; do
        if [ -f "$file" ]; then
            echo -n "  Checking $file... "
            
            # Specific checks for each file
            case "$file" in
                "package.json")
                    if grep -q '"name": "mai"' "$file"; then
                        echo -e "${GREEN}✓${NC}"
                    else
                        echo -e "${RED}✗${NC} - Missing mAI name"
                        sed -i '' 's/"name": "open-webui"/"name": "mai"/' "$file"
                        git add "$file"
                    fi
                    ;;
                *)
                    echo -e "${GREEN}✓${NC}"
                    ;;
            esac
        else
            echo -e "  Checking $file... ${RED}FILE NOT FOUND${NC}"
        fi
    done
}

run_tests() {
    log_info "Running build tests..."
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log_info "Installing dependencies..."
        npm ci --force
    fi
    
    # Run build
    log_info "Testing build..."
    if npm run build; then
        log_info "Build successful!"
    else
        log_error "Build failed! Please fix errors before continuing."
        exit 1
    fi
}

finalize_merge() {
    log_info "Finalizing merge..."
    
    # Create merge commit
    COMMIT_MSG="merge: update to Open WebUI ${LATEST_TAG} while preserving mAI customizations

- Merged upstream version ${LATEST_TAG}
- Preserved all mAI branding and features
- Maintained custom themes and patterns
- Kept Polish localization"
    
    git commit -m "$COMMIT_MSG"
    
    log_info "Merge completed successfully!"
    
    # Show summary
    echo -e "\n${GREEN}Summary:${NC}"
    echo "- Updated from ${CURRENT_VERSION} to ${LATEST_TAG}"
    echo "- Backup branch: ${BACKUP_BRANCH}"
    echo "- All customizations preserved"
    
    echo -e "\n${YELLOW}Next steps:${NC}"
    echo "1. Test the application thoroughly"
    echo "2. Update docs/customization/mai-changelog.md with changes"
    echo "3. Push to origin: git push origin ${DEV_BRANCH}"
    echo "4. Create PR for review"
}

continue_merge() {
    log_info "Continuing merge after conflict resolution..."
    
    # Check if we're in merge state
    if ! git status | grep -q "All conflicts fixed but you are still merging"; then
        log_error "Not in merge state. Run the update script without --continue first."
        exit 1
    fi
    
    apply_customizations
    run_tests
    finalize_merge
}

# Main execution
main() {
    echo -e "${GREEN}mAI Update Script${NC}"
    echo "===================="
    
    # Check for continue flag
    if [ "$1" == "--continue" ]; then
        continue_merge
        exit 0
    fi
    
    # Normal update flow
    check_prerequisites
    create_backup
    fetch_upstream
    
    # Ask for confirmation
    echo -e "\n${YELLOW}This will merge ${LATEST_TAG} into your current branch.${NC}"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Update cancelled."
        exit 0
    fi
    
    merge_upstream
    apply_customizations
    run_tests
    finalize_merge
}

# Run main function
main "$@"