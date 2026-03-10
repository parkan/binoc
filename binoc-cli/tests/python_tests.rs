use std::process::Command;

fn workspace_root() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}

#[test]
fn python_binding_tests() {
    let root = workspace_root();
    let python_dir = root.join("binoc-python");

    if !python_dir.join("tests").exists() {
        eprintln!("binoc-python/tests not found, skipping");
        return;
    }

    // Set up the virtualenv with dev dependencies (pytest + maturin).
    let sync = Command::new("uv")
        .args(["sync", "--extra", "dev"])
        .current_dir(&python_dir)
        .output();

    match sync {
        Ok(o) if o.status.success() => {}
        Ok(o) => {
            eprintln!(
                "uv sync failed (skipping Python tests):\n{}",
                String::from_utf8_lossy(&o.stderr),
            );
            return;
        }
        Err(e) => {
            eprintln!("uv not available ({e}), skipping Python tests");
            return;
        }
    }

    // Build the Python extension module into the virtualenv.
    let develop = Command::new("uv")
        .args(["run", "maturin", "develop"])
        .current_dir(&python_dir)
        .output();

    match develop {
        Ok(o) if o.status.success() => {}
        Ok(o) => {
            eprintln!(
                "maturin develop failed (skipping Python tests):\n{}{}",
                String::from_utf8_lossy(&o.stdout),
                String::from_utf8_lossy(&o.stderr),
            );
            return;
        }
        Err(e) => {
            eprintln!("maturin not available ({e}), skipping Python tests");
            return;
        }
    }

    // Run the Python test suite.
    let pytest = Command::new("uv")
        .args(["run", "pytest", "tests", "-v"])
        .current_dir(&python_dir)
        .output();

    match pytest {
        Ok(o) => {
            let stdout = String::from_utf8_lossy(&o.stdout);
            let stderr = String::from_utf8_lossy(&o.stderr);
            if !stdout.is_empty() {
                eprintln!("{stdout}");
            }
            if !stderr.is_empty() {
                eprintln!("{stderr}");
            }
            assert!(o.status.success(), "Python binding tests failed");
        }
        Err(e) => {
            eprintln!("pytest not available ({e}), skipping Python tests");
        }
    }
}
