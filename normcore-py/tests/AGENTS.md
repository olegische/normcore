# Tests Agent Contract

This document defines the **only valid authority** for test execution
and test-related modifications in this repository.

Any behavior outside this contract is invalid.

---

## Execution Authority

The **only allowed test command** is:

```
uv run --python .venv/bin/python --extra test -m pytest
```

- The command MUST be executed from the **worktree root**.
- No other test commands, flags, wrappers, or substitutions are allowed.
- The command MUST NOT be modified, extended, or partially reproduced.

---

## Environment Requirements

- Python version: **3.10 or higher**
- Dependencies:
  - Test dependencies MUST be installed via the `test` extra.
- If the command fails due to:
  - environment issues
  - missing dependencies
  - uv/runtime/sandbox limitations  
  this is considered an **execution failure**, not a test failure.

---

## Scope of Authority

### Allowed
- Creating or modifying files **only under `tests/`**
- Updating existing unit tests to reflect current behavior

### Forbidden
- Any modification to files outside `tests/`
- Any modification to production code (`src/`)
- Adding integration, e2e, or snapshot tests
- Skipping, xfail, or silencing failing tests
- Inventing APIs, behaviors, or side effects
- Changing project configuration or dependencies

---

## Failure Handling

If the test command cannot be executed successfully due to
non-test-related reasons (environment, tooling, permissions):

- The agent MUST STOP immediately.
- The agent MUST NOT attempt workarounds.
- The agent MUST NOT change the test command.
- The agent MUST report that **human intervention is required**.

---

## Responsibility Boundary

- This file defines **what is permitted**, not how to reason or act.
- Any test execution claim is valid **only if** it corresponds
  to the command defined above.
- Narrative claims without execution evidence are invalid.

---

## Definition of Valid Completion

A run is considered valid **only if**:
- The exact command specified above was executed.
- All tests completed successfully.
- All repository changes are confined to `tests/`.

Anything else is a contract violation.
