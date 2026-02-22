set shell := ["bash", "-cu"]
set working-directory := "normcore-rs"
set positional-arguments

# Display help
help:
    just -l

# Run the Rust CLI binary
run *args:
    cargo run -- "$@"

# Shortcut for evaluate subcommand
evaluate *args:
    cargo run -- evaluate "$@"

# format code
fmt:
    cargo fmt -- --config imports_granularity=Item 2>/dev/null

fmt-check:
    cargo fmt --all --check

fix *args:
    cargo clippy --fix --all-targets --all-features --tests --allow-dirty "$@"

clippy *args:
    cargo clippy --all-targets --all-features -- "$@"

clippy-strict:
    cargo clippy --all-targets --all-features -- -D warnings

install:
    rustup show active-toolchain
    cargo fetch

test:
    if command -v cargo-nextest >/dev/null 2>&1; then cargo nextest run --no-fail-fast; else cargo test --all-features; fi

rust-fmt:
    just fmt

rust-fmt-check:
    just fmt-check

rust-lint:
    just clippy-strict

rust-test:
    cargo test --all-features

rust-mutants *args:
    ../scripts/rust/run_mutants_rs.sh "$@"

rust-fuzz *args:
    ../scripts/rust/run_fuzz_rs.sh "$@"

formal-check:
    (cd ../formal/implementation && tlc -deadlock -workers 1 spec.tla && tlc -deadlock -workers 1 grounding_accounting.tla -config grounding_accounting.cfg)

formal-trace-export input output:
    python3 ../scripts/formal/tlc_trace_to_json.py --input "{{input}}" --output "{{output}}"

formal-replay trace_json:
    TRACE_REPLAY_JSON="{{trace_json}}" cargo test --test trace_replay replay_generated_formal_trace

check: fmt-check clippy-strict test
rust-check: rust-fmt-check rust-lint rust-test

# Publish Python package to TestPyPI from release branches
py-publish-test:
    branch="$(git branch --show-current)"; \
    if [[ ! "$branch" =~ ^release/ ]]; then \
      echo "ERROR: py-publish-test must run from release/* branch (current: $branch)" >&2; \
      exit 2; \
    fi; \
    ../scripts/python/publish_testpypi.sh

# Smoke TestPyPI package installation and evaluator flow
py-smoke-testpypi:
    PIP_INDEX_URL="https://test.pypi.org/simple/" \
    PIP_EXTRA_INDEX_URL="https://pypi.org/simple/" \
    ../scripts/python/smoke_codex_pypi_normcore.sh

# Release-branch Python flow: publish to TestPyPI, then smoke
py-release-test: py-publish-test py-smoke-testpypi

# Publish Python package to production PyPI from main only
py-publish:
    branch="$(git branch --show-current)"; \
    if [[ "$branch" != "main" ]]; then \
      echo "ERROR: py-publish must run from main branch (current: $branch)" >&2; \
      exit 2; \
    fi; \
    ../scripts/python/publish_pypi.sh

# Smoke production PyPI package installation and evaluator flow
py-smoke-pypi:
    ../scripts/python/smoke_codex_pypi_normcore.sh

# Main-branch Python flow: publish to PyPI, then smoke
py-main-release: py-publish py-smoke-pypi

# crates.io dry-run from Rust release branches
rs-publish-dry-run:
    branch="$(git branch --show-current)"; \
    if [[ ! "$branch" =~ ^release/rs/ ]]; then \
      echo "ERROR: rs-publish-dry-run must run from release/rs/* branch (current: $branch)" >&2; \
      exit 2; \
    fi; \
    cargo publish --dry-run --manifest-path Cargo.toml

# Smoke packaged .crate artifact locally
rs-smoke-artifact:
    ../scripts/rust/smoke_crate_artifact.sh

# Codex-driven Rust smoke flow
rs-smoke-codex:
    ../scripts/rust/smoke_codex_rust_local.sh

# Smoke published crates.io release via installed binary
rs-smoke-crates-io:
    ../scripts/rust/smoke_crates_io_published.sh

# Rust release-branch validation flow
rs-release-test: rust-check rs-publish-dry-run rs-smoke-artifact rs-smoke-codex

# Publish Rust crate to crates.io from main only
rs-publish:
    branch="$(git branch --show-current)"; \
    if [[ "$branch" != "main" ]]; then \
      echo "ERROR: rs-publish must run from main branch (current: $branch)" >&2; \
      exit 2; \
    fi; \
    ../scripts/rust/publish_crates_io.sh

# Main-branch Rust flow: publish to crates.io, then smoke the published crate
rs-main-release: rs-publish rs-smoke-crates-io
