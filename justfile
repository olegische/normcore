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
