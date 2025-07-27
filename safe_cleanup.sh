#!/bin/bash

# mAI Repository Safe Cleanup Script
# Removes unnecessary files while preserving development workflow
# Author: Auto-generated for mAI project safety

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLEANUP_DIR="/tmp/mai_cleanup_$(date +%Y%m%d_%H%M%S)"
REPO_DIR="$(pwd)"
BACKUP_BRANCH="cleanup-backup-$(date +%Y%m%d_%H%M%S)"

# Safety checks
check_safety_requirements() {
    echo -e "${BLUE}=== mAI Safe Cleanup Script ===${NC}"
    echo "Repository: $REPO_DIR"
    echo "Cleanup staging: $CLEANUP_DIR"
    echo ""
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}ERROR: Not in a git repository${NC}"
        exit 1
    fi
    
    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [[ "$CURRENT_BRANCH" != "customization" ]]; then
        echo -e "${RED}ERROR: Not on 'customization' branch (currently on: $CURRENT_BRANCH)${NC}"
        echo "Please switch to 'customization' branch first:"
        echo "  git checkout customization"
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}WARNING: You have uncommitted changes${NC}"
        echo "Current status:"
        git status --short
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Safety checks passed${NC}"
    echo ""
}

# Create Git checkpoint
create_checkpoint() {
    echo -e "${BLUE}Creating Git checkpoint...${NC}"
    
    # Add all files to staging
    git add .
    
    # Create checkpoint commit
    git commit -m "CHECKPOINT: Before cleanup - $(date +%Y-%m-%d_%H:%M:%S)" || true
    
    # Create backup branch
    git branch "$BACKUP_BRANCH" || true
    
    echo -e "${GREEN}✓ Checkpoint created on branch: $BACKUP_BRANCH${NC}"
    echo ""
}

# Setup cleanup directory
setup_cleanup_dir() {
    echo -e "${BLUE}Setting up cleanup staging directory...${NC}"
    mkdir -p "$CLEANUP_DIR"
    echo "Staging directory: $CLEANUP_DIR"
    echo ""
}

# Show file sizes helper
show_file_info() {
    local files=("$@")
    local total_size=0
    
    if [[ ${#files[@]} -eq 0 ]]; then
        echo "  No files found in this category"
        return
    fi
    
    echo "  Files to be moved:"
    for file in "${files[@]}"; do
        if [[ -e "$file" ]]; then
            local size=$(du -h "$file" | cut -f1)
            local size_bytes=$(du -b "$file" | cut -f1)
            total_size=$((total_size + size_bytes))
            echo "    $file ($size)"
        fi
    done
    
    if [[ $total_size -gt 0 ]]; then
        local total_human=$(numfmt --to=iec --suffix=B $total_size)
        echo "  Total size: $total_human"
    fi
}

# Move files safely
move_files_safely() {
    local category="$1"
    shift
    local files=("$@")
    
    if [[ ${#files[@]} -eq 0 ]]; then
        echo "  No files to move"
        return
    fi
    
    local category_dir="$CLEANUP_DIR/$category"
    mkdir -p "$category_dir"
    
    for file in "${files[@]}"; do
        if [[ -e "$file" ]]; then
            local dirname=$(dirname "$file")
            mkdir -p "$category_dir/$dirname"
            mv "$file" "$category_dir/$file"
            echo "    Moved: $file"
        fi
    done
}

# Category 1: System files (macOS junk)
cleanup_system_files() {
    echo -e "${YELLOW}=== Category 1: System Files (macOS junk) ===${NC}"
    
    # Find .DS_Store files
    local ds_store_files=()
    while IFS= read -r -d '' file; do
        ds_store_files+=("$file")
    done < <(find . -name ".DS_Store" -print0 2>/dev/null || true)
    
    show_file_info "${ds_store_files[@]}"
    
    if [[ ${#ds_store_files[@]} -gt 0 ]]; then
        echo ""
        read -p "Remove macOS .DS_Store files? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            move_files_safely "system_files" "${ds_store_files[@]}"
            echo -e "${GREEN}✓ System files moved to staging${NC}"
        else
            echo "Skipped system files"
        fi
    fi
    echo ""
}

# Category 2: Old backups and documents
cleanup_old_backups() {
    echo -e "${YELLOW}=== Category 2: Old Backups and Documents ===${NC}"
    
    local backup_files=()
    
    # Check for specific backup files
    [[ -f "webui_backup_20250725_182230.db" ]] && backup_files+=("webui_backup_20250725_182230.db")
    
    # Check backups/ directory (only if it contains just .DS_Store)
    if [[ -d "backups" ]]; then
        local backup_contents=$(find backups -type f ! -name ".DS_Store" 2>/dev/null | wc -l)
        if [[ $backup_contents -eq 0 ]]; then
            backup_files+=("backups")
        fi
    fi
    
    # Check customization-backup/ directory
    [[ -d "customization-backup" ]] && backup_files+=("customization-backup")
    
    show_file_info "${backup_files[@]}"
    
    if [[ ${#backup_files[@]} -gt 0 ]]; then
        echo ""
        read -p "Remove old backup files and directories? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            move_files_safely "old_backups" "${backup_files[@]}"
            echo -e "${GREEN}✓ Old backups moved to staging${NC}"
        else
            echo "Skipped old backups"
        fi
    fi
    echo ""
}

# Category 3: Completed task documentation
cleanup_completed_docs() {
    echo -e "${YELLOW}=== Category 3: Completed Task Documentation ===${NC}"
    
    local doc_files=()
    [[ -f "COMPONENT_COMPOSITION_SUCCESS_REPORT.md" ]] && doc_files+=("COMPONENT_COMPOSITION_SUCCESS_REPORT.md")
    [[ -f "reorganization_plan.md" ]] && doc_files+=("reorganization_plan.md")
    
    show_file_info "${doc_files[@]}"
    
    if [[ ${#doc_files[@]} -gt 0 ]]; then
        echo ""
        read -p "Remove completed task documentation? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            move_files_safely "completed_docs" "${doc_files[@]}"
            echo -e "${GREEN}✓ Completed documentation moved to staging${NC}"
        else
            echo "Skipped completed documentation"
        fi
    fi
    echo ""
}

# Category 4: One-time scripts (Optional)
cleanup_onetime_scripts() {
    echo -e "${YELLOW}=== Category 4: One-time Scripts (OPTIONAL) ===${NC}"
    
    local script_files=()
    [[ -f "test_pricing_api.sh" ]] && script_files+=("test_pricing_api.sh")
    [[ -f "cleanup_backup_scripts.sh" ]] && script_files+=("cleanup_backup_scripts.sh")
    
    show_file_info "${script_files[@]}"
    
    if [[ ${#script_files[@]} -gt 0 ]]; then
        echo ""
        echo -e "${BLUE}Note: You can also move test_pricing_api.sh to tools/ directory instead${NC}"
        read -p "Remove one-time scripts? (y/n/move): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            move_files_safely "onetime_scripts" "${script_files[@]}"
            echo -e "${GREEN}✓ One-time scripts moved to staging${NC}"
        elif [[ $REPLY =~ ^[Mm]$ ]] && [[ -f "test_pricing_api.sh" ]]; then
            mkdir -p tools
            mv test_pricing_api.sh tools/
            echo -e "${GREEN}✓ test_pricing_api.sh moved to tools/${NC}"
            # Remove from array and move remaining
            script_files=("${script_files[@]/test_pricing_api.sh}")
            if [[ ${#script_files[@]} -gt 0 ]]; then
                move_files_safely "onetime_scripts" "${script_files[@]}"
            fi
        else
            echo "Skipped one-time scripts"
        fi
    fi
    echo ""
}

# Show summary and rollback instructions
show_summary() {
    echo -e "${BLUE}=== Cleanup Summary ===${NC}"
    
    if [[ -d "$CLEANUP_DIR" ]] && [[ -n "$(ls -A "$CLEANUP_DIR" 2>/dev/null)" ]]; then
        echo "Files moved to: $CLEANUP_DIR"
        echo ""
        echo "Directory structure:"
        tree "$CLEANUP_DIR" 2>/dev/null || find "$CLEANUP_DIR" -type f
        echo ""
        
        local total_size=$(du -sh "$CLEANUP_DIR" | cut -f1)
        echo "Total space that will be freed: $total_size"
        echo ""
        
        echo -e "${YELLOW}=== ROLLBACK INSTRUCTIONS ===${NC}"
        echo "If you need to restore any files:"
        echo "1. Files are safely stored in: $CLEANUP_DIR"
        echo "2. Git checkpoint branch: $BACKUP_BRANCH"
        echo "3. To restore all files:"
        echo "   cp -r \"$CLEANUP_DIR\"/* ."
        echo "4. To restore from git:"
        echo "   git checkout $BACKUP_BRANCH"
        echo ""
        
        read -p "Permanently delete staged files? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$CLEANUP_DIR"
            echo -e "${GREEN}✓ Cleanup completed - files permanently deleted${NC}"
            echo -e "${BLUE}Git checkpoint branch '$BACKUP_BRANCH' preserved for safety${NC}"
        else
            echo -e "${YELLOW}Files preserved in: $CLEANUP_DIR${NC}"
            echo "You can manually delete this directory later if desired"
        fi
    else
        echo "No files were moved - nothing to clean up"
        rm -rf "$CLEANUP_DIR" 2>/dev/null || true
    fi
}

# Main execution
main() {
    check_safety_requirements
    create_checkpoint
    setup_cleanup_dir
    
    cleanup_system_files
    cleanup_old_backups
    cleanup_completed_docs
    cleanup_onetime_scripts
    
    show_summary
    
    echo ""
    echo -e "${GREEN}✓ Safe cleanup completed${NC}"
    echo "Development workflow preserved - all caches and build artifacts intact"
}

# Run main function
main "$@"