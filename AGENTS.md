# AI Agent Instructions

This file contains instructions for AI coding agents working on this terminal app template project.

## Development Commands

**Environment Setup:**
```bash
# Activate virtual environment (required for all commands)
source .venv/bin/activate

# Install dependencies
pip install typer rich pynput pyautogui pyperclip requests Pillow python-daemon toml flake8 pytest pyinstaller
```

**Testing:**
```bash
# Run all tests
python -m pytest -v

# Run specific test file
python -m pytest tests/test_config.py -v

# Test CLI manually
python -m app.cli --help
python -m app.cli action screenshot.full
```

**Building Executables:**
```bash
# PyInstaller - creates a single executable file
pyinstaller --onefile --name aio_terminal_template --add-data "config.toml:." app/cli.py

# Test the built executable
./dist/aio_terminal_template --help
```

## Project Structure

- **Entry point:** `app/cli.py` (Typer-based CLI)
- **Actions:** `app/actions/` (auto-discovered modules)
- **Shortcuts:** `app/shortcuts/manager.py` (pynput global hotkeys)  
- **Config:** `app/core/config.py` (TOML with local overrides)
- **Tests:** `tests/` (pytest with 34 tests covering all modules)

## Code Conventions

- **CLI framework:** Typer
- **UI framework:** Rich
- **Config format:** TOML with deep merging
- **Test framework:** pytest with unittest.mock
- **Import style:** `from app.module import function`
- **Action signature:** `def action_name(config): return "result"`

## Build System

**PyInstaller**: Industry standard Python packaging tool that creates single executable files
- Single ~16MB file
- Cross-platform (Linux, macOS, Windows)
- Zero dependencies on target machines
- Auto-dependency detection

## Testing Strategy

- **Unit tests** for all core modules (config, registry, shortcuts)
- **CLI tests** using Typer's testing framework
- **Mock-based testing** for system dependencies (filesystem, shortcuts)
- **Integration tests** for action execution
- **Build verification** tests for executables

## Common Tasks

**Adding new action:**
1. Create `app/actions/my_action.py`
2. Define `def my_function(config): ...`
3. Test with `python -m app.cli action my_function`

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
