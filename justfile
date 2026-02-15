set shell := ["bash", "-cu"]
set working-directory := "src/normcore-rs"
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

check: fmt-check clippy-strict test
rust-check: rust-fmt-check rust-lint rust-test
