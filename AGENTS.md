# AI Agent Instructions for Meetscribe

This file contains instructions for AI coding agents working on the Meetscribe project.

## Development Commands

**Environment Setup:**
```bash
# Activate virtual environment (required for all commands)
source .venv/bin/activate

# Install dependencies
pip install typer rich toml deepgram-sdk flake8 pytest pyinstaller
```

**Testing:**
```bash
# Run all tests
python -m pytest -v

# Run specific test file
python -m pytest tests/test_config.py -v

# Test CLI manually
python -m app.cli --help
python -m app.cli process dir /path/to/audio/files
```

**Building Executables:**
```bash
# PyInstaller - creates a single executable file
pyinstaller --onefile --name meetscribe --add-data "config.toml:." app/cli.py

# Test the built executable
./dist/meetscribe --help
```

## Project Structure

- **Entry point:** `app/cli.py` (Typer-based CLI)
- **Transcriber:** `app/transcriber.py` (Deepgram integration)
- **Core:** `app/core/` (config, logging, context)
- **Tests:** `tests/` (pytest with comprehensive test coverage)

## Code Conventions

- **CLI framework:** Typer
- **UI framework:** Rich
- **Config format:** TOML with deep merging
- **Test framework:** pytest with unittest.mock
- **Import style:** `from app.module import function`
- **Module structure:** Clean separation of concerns with dependency injection

## Build System

**PyInstaller**: Industry standard Python packaging tool that creates single executable files
- Single ~16MB file
- Cross-platform (Linux, macOS, Windows)
- Zero dependencies on target machines
- Auto-dependency detection

## Testing Strategy

- **Unit tests** for all core modules (config, logging, context)
- **CLI tests** using Typer's testing framework
- **Mock-based testing** for external services (Deepgram API)
- **Integration tests** for audio processing workflows
- **Build verification** tests for executables

## Common Tasks

**Adding new features:**
1. Create new modules in `app/` directory
2. Add CLI commands in `app/cli.py`
3. Test with `python -m app.cli --help`

**Debugging build issues:**
1. Check virtual environment is activated
2. Use PyInstaller spec file for consistent builds
3. Check dependencies with `pip list`
4. Test with `python -m app.cli --help` before building

## Performance Notes

- **Startup time:** ~0.5s
- **File size:** ~16MB single executable
- **Cross-platform:** Works on Linux, macOS, and Windows
- **Build time:** ~30s
