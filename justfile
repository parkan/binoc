# Build everything: Rust workspace + Python bindings.
build:
    cargo build --release
    cd binoc-python && uv sync --extra dev

# Run all tests: Rust crates + Python binding tests.
test:
    cargo test
    cd binoc-python && uv run pytest

# Regenerate docs/tutorial.md by re-running all embedded code blocks.
docs:
    #!/usr/bin/env bash
    set -euo pipefail
    if uvx showboat verify docs/tutorial.md --output docs/tutorial.md > /dev/null 2>&1; then
        echo "docs/tutorial.md is up to date."
    else
        echo "docs/tutorial.md updated."
    fi

# Review pending snapshot changes interactively.
snapshot-review:
    cargo insta test -p binoc-stdlib --test test_vectors --review

# Regenerate all expected-output snapshots (run after intentional IR/output changes).
snapshot-update:
    INSTA_UPDATE=always cargo test -p binoc-stdlib --test test_vectors
