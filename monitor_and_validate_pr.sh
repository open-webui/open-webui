#!/bin/bash
set -e

REPO="jjdrisco/DSL-kidsgpt-open-webui"
BRANCH="feature/separate-quiz-workflow"
BASE="main"

echo "=========================================="
echo "PR Monitor and Validator"
echo "=========================================="
echo "Branch: $BRANCH -> $BASE"
echo "PR Creation URL: https://github.com/$REPO/compare/$BASE...$BRANCH?expand=1"
echo ""

# Function to check for PR
check_pr() {
    gh pr list --head "$BRANCH" --json number --jq '.[0].number' 2>/dev/null || echo ""
}

# Function to get PR status
get_pr_status() {
    local pr_num=$1
    gh pr view $pr_num --json state,mergeable,mergeStateStatus,statusCheckRollup --jq '{state: .state, mergeable: .mergeable, mergeStateStatus: .mergeStateStatus}' 2>/dev/null
}

# Function to check CI status
check_ci() {
    local pr_num=$1
    gh pr checks $pr_num --json name,status,conclusion 2>/dev/null || echo "[]"
}

# Wait for PR to be created
echo "Waiting for PR to be created..."
ATTEMPT=0
MAX_WAIT=120  # 2 minutes

while [ $ATTEMPT -lt $MAX_WAIT ]; do
    PR_NUM=$(check_pr)
    
    if [ -n "$PR_NUM" ] && [ "$PR_NUM" != "null" ] && [ "$PR_NUM" != "" ]; then
        echo "✓ PR found: #$PR_NUM"
        gh pr view $PR_NUM
        break
    fi
    
    if [ $((ATTEMPT % 20)) -eq 0 ] && [ $ATTEMPT -gt 0 ]; then
        echo "Still waiting... (${ATTEMPT}s elapsed)"
        echo "Create PR at: https://github.com/$REPO/compare/$BASE...$BRANCH?expand=1"
    fi
    
    sleep 2
    ATTEMPT=$((ATTEMPT + 2))
done

if [ -z "$PR_NUM" ] || [ "$PR_NUM" == "null" ] || [ "$PR_NUM" == "" ]; then
    echo ""
    echo "⚠ PR not found after waiting. Please create it manually:"
    echo "https://github.com/$REPO/compare/$BASE...$BRANCH?expand=1"
    exit 1
fi

echo ""
echo "=========================================="
echo "Monitoring PR #$PR_NUM"
echo "=========================================="

# Monitor and fix until ready
ITERATION=0
MAX_ITERATIONS=200  # ~33 minutes max

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    echo ""
    echo "[$(date +%H:%M:%S)] Check #$((ITERATION + 1))"
    
    # Get CI status
    CI_STATUS=$(check_ci $PR_NUM)
    FAILING_CHECKS=$(echo "$CI_STATUS" | jq -r '.[] | select(.conclusion == "failure") | .name' 2>/dev/null || echo "")
    PENDING_CHECKS=$(echo "$CI_STATUS" | jq -r '.[] | select(.status == "in_progress" or .status == "queued" or .conclusion == null) | .name' 2>/dev/null || echo "")
    PASSING_CHECKS=$(echo "$CI_STATUS" | jq -r '.[] | select(.conclusion == "success") | .name' 2>/dev/null || echo "")
    
    if [ -n "$FAILING_CHECKS" ]; then
        echo "⚠ Failing checks:"
        echo "$FAILING_CHECKS" | while read check; do
            echo "  - $check"
        done
        echo ""
        echo "Investigating failures..."
        
        # Check out the branch and investigate
        cd /workspace
        git checkout $BRANCH
        
        # Get detailed check information
        echo ""
        echo "Detailed check status:"
        gh pr checks $PR_NUM --json name,status,conclusion,detailsUrl | jq -r '.[] | "\(.name): \(.status) - \(.conclusion // "pending") - \(.detailsUrl // "")"' 2>/dev/null || echo "Could not get detailed status"
        
        # Try to identify common issues
        if echo "$FAILING_CHECKS" | grep -qi "test\|cypress\|lint"; then
            echo ""
            echo "Test/lint failures detected. Running local checks..."
            # Add specific fix logic here based on error type
        fi
        
    elif [ -n "$PENDING_CHECKS" ]; then
        echo "⏳ Pending checks:"
        echo "$PENDING_CHECKS" | head -5 | while read check; do
            echo "  - $check"
        done
        [ $(echo "$PENDING_CHECKS" | wc -l) -gt 5 ] && echo "  ... and more"
        
    else
        # Check if mergeable
        PR_INFO=$(get_pr_status $PR_NUM)
        MERGEABLE=$(echo "$PR_INFO" | jq -r '.mergeable' 2>/dev/null || echo "unknown")
        STATE=$(echo "$PR_INFO" | jq -r '.state' 2>/dev/null || echo "unknown")
        
        if [ "$STATE" == "MERGED" ]; then
            echo "✓ PR has been merged!"
            break
        elif [ "$MERGEABLE" == "true" ] && [ -z "$FAILING_CHECKS" ] && [ -z "$PENDING_CHECKS" ]; then
            echo "✓ All checks passing and PR is mergeable!"
            echo ""
            echo "Attempting to merge PR #$PR_NUM..."
            
            # Try to merge
            MERGE_RESULT=$(gh pr merge $PR_NUM --squash --delete-branch=false 2>&1 || gh pr merge $PR_NUM --merge --delete-branch=false 2>&1)
            
            if echo "$MERGE_RESULT" | grep -qi "merged\|already merged"; then
                echo ""
                echo "✓ PR merged successfully!"
                gh pr view $PR_NUM
                break
            else
                echo "Merge result: $MERGE_RESULT"
                echo "PR may require manual merge or approval"
            fi
        fi
    fi
    
    sleep 10
    ITERATION=$((ITERATION + 1))
done

if [ $ITERATION -ge $MAX_ITERATIONS ]; then
    echo ""
    echo "⚠ Reached maximum iterations. PR status:"
    gh pr view $PR_NUM
    echo ""
    echo "CI Status:"
    gh pr checks $PR_NUM
fi
