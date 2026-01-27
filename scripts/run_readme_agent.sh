#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[INFO] $1"
}

fail() {
  echo "[ERROR] $1" >&2
  exit 1
}

# =========================
# CONFIG
# =========================
PROFILE="section_rewrite"
ROOT="content_pipeline/02_tracks/arxiv_formal/ai-space"
DRAFT="$ROOT/draft/ai_space_v02.md"
SECTIONS_DIR="$ROOT/sections"

# =========================
# INPUT
# =========================
SECTION_RAW="${1:?usage: $0 \"<Section title>\"}"

log "Section raw: $SECTION_RAW"

# =========================
# NORMALIZE SECTION NAME
# =========================
SECTION_KB="$(echo "$SECTION_RAW" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's/[^a-z0-9]+/-/g' \
  | sed -E 's/^-+|-+$//g')"

log "Section kebab: $SECTION_KB"

BRANCH="docs/$SECTION_KB"
WORKTREE_DIR=".worktrees/$SECTION_KB"
SECTION_OUT_DIR="$SECTIONS_DIR/$SECTION_KB"

log "Branch: $BRANCH"
log "Worktree dir: $WORKTREE_DIR"

# =========================
# SANITY CHECKS
# =========================
command -v codex >/dev/null || fail "codex not found"
command -v git   >/dev/null || fail "git not found"

log "Checking git repository"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || fail "Not inside a git repository"

[ -f "$DRAFT" ] || fail "Draft not found: $DRAFT"

# =========================
# CREATE WORKTREE
# =========================
log "Preparing worktree"
mkdir -p .worktrees
log ".worktrees directory ensured"

log "Checking if branch exists"
if git show-ref --quiet "refs/heads/$BRANCH"; then
  log "Branch already exists: $BRANCH"
else
  log "Creating branch: $BRANCH"
  git branch "$BRANCH" || fail "git branch failed"
  log "Branch created"
fi

log "Checking if worktree exists"
if [ -d "$WORKTREE_DIR" ]; then
  log "Worktree already exists: $WORKTREE_DIR"
else
  log "Adding worktree: $WORKTREE_DIR"
  git worktree add "$WORKTREE_DIR" "$BRANCH" || fail "git worktree add failed"
  log "Worktree created"
fi

# =========================
# CREATE SECTION DIRECTORY
# =========================
log "Creating section output directory"
mkdir -p "$WORKTREE_DIR/$SECTION_OUT_DIR"
log "Section directory ready"

# =========================
# PROMPT
# =========================
log "Building prompt"

PROMPT="$(cat <<EOF
You are working on a scientific paper.

Target section:
"$SECTION_RAW"

Tasks:
1. Read the full draft at:
   $DRAFT
2. Locate the section titled "$SECTION_RAW".
3. Understand its role in the overall paper.
4. Search for relevant peer-reviewed literature:
   - Prefer arXiv papers and established journals.
   - Ignore blog posts, opinion pieces, or marketing material.
5. Analyze how existing work relates to the paper's thesis.
6. Rewrite the section as a high-quality scientific section.

Rules:
- Do NOT invent citations.
- If you use information from web search, include a direct URL.
- Prefer arXiv or journal URLs.
- If no strong sources exist, state this explicitly.
- Do not modify other sections.

Output:
- Write the final section to:
  $SECTION_OUT_DIR/section.md
- Markdown only.
EOF
)"

log "Prompt built"

# =========================
# RUN CODEX
# =========================
log "Changing directory to worktree"
cd "$WORKTREE_DIR"

LOG="codex_${SECTION_KB}.log"

log "Launching Codex"
log "Profile: $PROFILE"
log "PWD: $(pwd)"
log "Log file: $LOG"

echo "$PROMPT" | codex exec \
  --profile "$PROFILE" \
  --cd "." \
  --skip-git-repo-check \
  --json \
  2>&1 | tee "$LOG"

log "Codex process exited"