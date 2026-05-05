# Sync Audio Assets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Copy latest audio files from m3llm repository and create a PR.

**Architecture:** Automated copy from local m3llm repo to current repo.

**Tech Stack:** Git, Bash, GitHub CLI.

---

### Task 1: Update Source Repository

**Files:**
- Read: `/home/cyber/Desktop/m3llm`

**Step 1: Ensure main branch and pull latest**

Run: `cd /home/cyber/Desktop/m3llm && git checkout main && git pull`
Expected: "Already up to date." or successful pull.

**Step 2: Commit (not needed for source repo)**

---

### Task 2: Prepare Destination Branch

**Files:**
- Modify: Current repository branch

**Step 1: Create new branch**

Run: `git checkout -b update-static-audio`
Expected: Switched to a new branch 'update-static-audio'

---

### Task 3: Sync Assets

**Files:**
- Modify: `static/audio/`

**Step 1: Copy audio files**

Run: `cp -v /home/cyber/Desktop/m3llm/static/audio/* static/audio/`
Expected: List of copied files including error.mp3, greeting.mp3, etc.

**Step 2: Verify files exist**

Run: `ls -l static/audio/`
Expected: List of files including the ones from m3llm.

**Step 3: Commit changes**

Run: `git add static/audio/ && git commit -m "feat(assets): update audio files from m3llm"`
Expected: [update-static-audio ...] feat(assets): update audio files from m3llm

---

### Task 4: Create Pull Request

**Files:**
- Create: GitHub PR

**Step 1: Push branch**

Run: `git push origin update-static-audio`
Expected: Branch pushed to remote.

**Step 2: Create PR**

Run: `gh pr create --title "feat(assets): update audio files from m3llm" --body "This PR updates the static audio assets by syncing them with the latest changes from the m3llm repository."`
Expected: PR URL returned.

