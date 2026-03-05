fn main() -> Result<(), Box<dyn std::error::Error>> {
    binoc_cli::run(binoc_stdlib::default_registry(), std::env::args_os())
}
