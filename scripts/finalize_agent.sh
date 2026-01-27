#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[INFO] $1"
}

warn() {
  echo "[WARN] $1" >&2
}

fail() {
  echo "[ERROR] $1" >&2
  exit 1
}

# =========================
# CONFIG
# =========================
ROOT="content_pipeline/02_tracks/arxiv_formal/ai-space"
SECTIONS_DIR="$ROOT/sections"
WORKTREES_DIR=".worktrees"
BRANCH_PREFIX="docs/"

# =========================
# SANITY CHECKS
# =========================
command -v git >/dev/null || fail "git not found"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || fail "Not inside a git repository"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$CURRENT_BRANCH" = "main" ] || fail "Run this script from the main branch"

if [ -n "$(git status --porcelain)" ]; then
  fail "Working tree not clean. Commit or stash changes before running this script."
fi

BRANCHES="$(git for-each-ref --format='%(refname:short)' "refs/heads/${BRANCH_PREFIX}*")"
if [ -z "$BRANCHES" ]; then
  fail "No ${BRANCH_PREFIX} branches found. Expected existing docs branches (e.g. docs/1-introduction)."
fi

# =========================
# COMMIT SECTION OUTPUTS
# =========================
log "Finalizing section outputs in docs branches"

for b in $BRANCHES; do
  section="${b#${BRANCH_PREFIX}}"
  wt="$WORKTREES_DIR/$section"

  log "Processing $b"

  if [ ! -d "$wt" ]; then
    log "Worktree missing, creating: $wt"
    git worktree add "$wt" "$b" || fail "git worktree add failed for $b"
  fi

  # Remove Codex logs if present
  rm -f "$wt"/codex_*.log || true

  src="$wt/$SECTIONS_DIR/$section/section.md"
  dst="$wt/$SECTIONS_DIR/$section.md"

  if [ -f "$src" ]; then
    log "Flattening: $SECTIONS_DIR/$section/section.md -> $SECTIONS_DIR/$section.md"
    git -C "$wt" mv "$SECTIONS_DIR/$section/section.md" "$SECTIONS_DIR/$section.md"
    rmdir -p "$wt/$SECTIONS_DIR/$section" 2>/dev/null || true
  else
    if [ -f "$dst" ]; then
      log "Already flat: $SECTIONS_DIR/$section.md"
    else
      warn "No section file found for $b"
    fi
  fi

  if [ -n "$(git -C "$wt" status --porcelain)" ]; then
    git -C "$wt" add -A
    git -C "$wt" commit -m "docs(${section}): finalize section"
  else
    log "No changes to commit in $b"
  fi

done

# =========================
# MERGE INTO MAIN
# =========================
log "Merging docs branches into main"
for b in $BRANCHES; do
  log "Merging $b"
  git merge --no-edit "$b"
done

# =========================
# CLEANUP WORKTREES + BRANCHES
# =========================
log "Cleaning up worktrees"
for b in $BRANCHES; do
  section="${b#${BRANCH_PREFIX}}"
  wt="$WORKTREES_DIR/$section"
  if [ -d "$wt" ]; then
    git worktree remove --force "$wt"
  fi

done

log "Deleting docs branches"
for b in $BRANCHES; do
  git branch -D "$b"
done

log "Done"
