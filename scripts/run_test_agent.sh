#!/usr/bin/env bash
set -euo pipefail

log()  { echo "[INFO] $1"; }
fail() { echo "[ERROR] $1" >&2; exit 1; }

# =========================
# CONFIG
# =========================
PROFILE="tests_unit"

BASE_REF="dev"
TEST_BRANCH="tests/unit"

WORKTREE_ROOT=".git-worktrees"
WORKTREE_DIR="$WORKTREE_ROOT/tests-unit"

# =========================
# SANITY CHECKS (HOST SAFE)
# =========================
command -v codex >/dev/null || fail "codex not found"
command -v git   >/dev/null || fail "git not found"

git rev-parse --is-inside-work-tree >/dev/null \
  || fail "Not inside a git repository"

git show-ref --verify --quiet "refs/heads/$BASE_REF" \
  || fail "Base ref '$BASE_REF' does not exist"

# =========================
# PREPARE WORKTREE (NO HOST MUTATION)
# =========================
log "Preparing worktree directory"
mkdir -p "$WORKTREE_ROOT"

if [ ! -d "$WORKTREE_DIR" ]; then
  log "Creating worktree from $BASE_REF"
  git worktree add "$WORKTREE_DIR" "$BASE_REF"

  (
    cd "$WORKTREE_DIR"
    git checkout -b "$TEST_BRANCH"
  )
else
  log "Worktree already exists: $WORKTREE_DIR"
fi

# =========================
# MERGE dev → tests/unit (WORKTREE ONLY)
# =========================
log "Merging $BASE_REF into $TEST_BRANCH inside worktree"
(
  cd "$WORKTREE_DIR"
  git merge --no-edit "$BASE_REF" \
    || fail "Merge conflict inside worktree — resolve manually"
)

# =========================
# WORKTREE-LOCAL UV CACHE (CRITICAL FIX)
# =========================
cd "$WORKTREE_DIR"

export UV_CACHE_DIR="$PWD/.uv-cache"
mkdir -p "$UV_CACHE_DIR"

log "Using UV_CACHE_DIR=$UV_CACHE_DIR"

# =========================
# INPUT STATE FINGERPRINTS
# =========================

hash_tree() {
  local path="$1"
  find "$path" -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    | sha256sum \
    | awk '{print $1}'
}

AGENTS_HASH="$(sha256sum tests/AGENTS.md | awk '{print $1}')"
SRC_HASH="$(hash_tree src)"
TESTS_HASH="$(hash_tree tests)"

log "AGENTS.md hash: $AGENTS_HASH"
log "src/ tree hash: $SRC_HASH"
log "tests/ tree hash (pre): $TESTS_HASH"

# =========================
# PROMPT (AGENTS.md IS THE ONLY AUTHORITY)
# =========================
PROMPT="$(cat <<'EOF'
You are a test-maintenance execution agent.

Your role is to align the unit test suite with the current behavior
of the production code, operating strictly within defined boundaries.

This prompt describes an execution strategy.
It does NOT grant authority.

---

## Authority and Precedence

- The ONLY normative authority for test execution and test-related permissions
  is the file `tests/AGENTS.md`.
- You MUST read `tests/AGENTS.md` before taking any action.
- You MUST treat it as a binding contract, not guidance.

If any instruction in this prompt conflicts with `tests/AGENTS.md`,
the instructions in `tests/AGENTS.md` take precedence.

---

## Execution Context (Non-Normative)

The current execution is bound to a specific snapshot of:
- `tests/AGENTS.md`
- `src/`
- `tests/`

Do not assume changes outside this snapshot.
Do not rely on unstated external state.

---

## Project Layout

- Production code: `src/`
- Unit tests: `tests/`

---

## Scope Constraints

You MAY:
- Create or modify files under `tests/` only.

You MUST NOT:
- Modify any file outside `tests/`.
- Modify production code under `src/`.
- Introduce integration, e2e, or snapshot tests.
- Skip, xfail, or silence failing tests.
- Invent APIs, behaviors, or side effects.
- Change project configuration or dependencies.

---

## Execution Strategy (Non-Normative)

The following describes one acceptable way to proceed.
It does not expand your authority.

1. Inspect production code under `src/` to identify externally visible behavior.
2. Inspect existing unit tests under `tests/`.
3. For each such behavior:
   - Ensure a corresponding unit test exists.
   - If a test exists but no longer reflects current behavior, update it.
   - If a test is missing, create a new one.
4. Preserve existing test style and conventions.
5. Do NOT delete existing tests.

---

## Test Execution

- Determine the test command STRICTLY from `tests/AGENTS.md`.
- Execute the command exactly as specified there.

If tests fail due to test logic:
- Fix ONLY the tests.
- Re-run the SAME command.
- Repeat until tests pass or no consistent update is possible.

If the test command fails due to environment, tooling, permissions,
uv/runtime issues, or sandbox limitations unrelated to test logic:
- STOP immediately.
- Do NOT attempt workarounds.
- Do NOT modify the command.
- Leave the repository in a consistent state.

---

## Completion Criteria

Your work is complete only if:
- All repository changes are confined to `tests/`.
- The exact test command defined in `tests/AGENTS.md` was executed.
- The last execution completed successfully.

If execution could not be completed,
report that human intervention is required.

Do NOT claim successful verification without execution.
EOF
)"

# =========================
# RUN CODEX (WORKTREE ONLY)
# =========================
LOG="codex_tests_unit.log"

log "Launching Codex unit-test agent"
log "Profile: $PROFILE"
log "PWD: $(pwd)"
log "Log file: $LOG"

# Run Codex (capture exit code correctly with pipe)
set +e
echo "$PROMPT" | codex exec \
  --profile "$PROFILE" \
  --cd "." \
  --skip-git-repo-check \
  --json \
  2>&1 | tee "$LOG"
CODEX_EXIT=${PIPESTATUS[0]}
set -e

log "Codex exit code: $CODEX_EXIT"
log "Codex finished"

# =========================
# POST-RUN STATE FINGERPRINTS
# =========================
POST_TESTS_HASH="$(hash_tree tests)"
POST_SRC_HASH="$(hash_tree src)"

log "tests/ tree hash (pre):  $TESTS_HASH"
log "tests/ tree hash (post): $POST_TESTS_HASH"
log "src/ tree hash (pre):    $SRC_HASH"
log "src/ tree hash (post):   $POST_SRC_HASH"

# =========================
# CONTRACT ENFORCEMENT
# =========================

# 1) src/ MUST NOT be modified
if [ "$SRC_HASH" != "$POST_SRC_HASH" ]; then
  log "CONTRACT VIOLATION: src/ was modified by the agent"
  log "Rolling back worktree due to contract violation"

  git reset --hard HEAD
  git clean -fd

  exit 3
fi

# =========================
# VERIFY TEST COMMAND EXECUTION
# =========================

EXPECTED_CMD="uv run --python .venv/bin/python --extra test -m pytest"

if ! grep -q "\"command\":.*${EXPECTED_CMD}" "$LOG"; then
  log "RUN RESULT: EXECUTION FAILURE (authorized test command not executed)"
  log "Rolling back worktree due to execution failure"

  git reset --hard HEAD
  git clean -fd

  exit 2
fi

# =========================
# RUN RESULT CLASSIFICATION
# =========================

# SUCCESS: tests executed and passed
if [ "$CODEX_EXIT" -eq 0 ]; then
  log "RUN RESULT: SUCCESS"
  log ""

  # =========================
  # HUMAN ACCEPTANCE SUMMARY
  # =========================
  log "================= HUMAN ACTION REQUIRED ================="
  log "RESULT:           ACCEPTANCE SUCCESS"
  log ""
  log "WHAT WAS CHECKED:"
  log "  - Source snapshot (src):   $SRC_HASH"
  log "  - Tests snapshot (before): $TESTS_HASH"
  log "  - Tests snapshot (after):  $POST_TESTS_HASH"
  log ""
  log "EXECUTION FACTS:"
  log "  - Authorized test command executed: YES"
  log "  - All tests passed:                 YES"
  log "  - Production code modified:         NO"
  log "  - Test files modified in this run:  NO"
  log ""
  log "DECISION TAKEN BY SYSTEM:"
  log "  -> Current test suite is VALID for this source snapshot."
  log "  -> State has been ACCEPTED."
  log ""
  log "WHAT YOU SHOULD DO NEXT:"
  log "  - Review the acceptance commit message."
  log "  - Merge or push the commit when ready."
  log "  - No Fix Agent action is required."
  log ""
  log "WHAT YOU SHOULD NOT DO:"
  log "  - Do NOT modify src/ based on this run."
  log "  - Do NOT rerun the test agent unless src/ changes."
  log "========================================================="
  log ""

  # =========================
  # ACCEPTANCE COMMIT
  # =========================
  COMMIT_MSG=$(cat <<EOF
tests(accept): validate tests against src snapshot

src_hash:   $SRC_HASH
tests_pre: $TESTS_HASH
tests_post:$POST_TESTS_HASH
EOF
)

  log "Creating acceptance commit"
  git add tests/
  git commit -m "$COMMIT_MSG"

  exit 0
fi

# EXECUTION FAILURE: tooling / environment / sandbox
if grep -q '"event":"tool_error"' "$LOG" \
   || grep -qi 'environment\|sandbox\|permission\|uv' "$LOG"; then
  log "RUN RESULT: EXECUTION FAILURE"
  log "Rolling back worktree due to execution failure"

  git reset --hard HEAD
  git clean -fd

  exit 2
fi

# Otherwise: tests executed but failed (valid outcome)
log "RUN RESULT: TEST FAILURE"
exit 1
