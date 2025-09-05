# Developer Guide

This guide provides step-by-step instructions for setting up the development environment and getting the basic version running.

## Prerequisites

- Python 3.10 or higher
- Git
- Terminal/Command Prompt

## Quick Start

### 1. Clone and Navigate to Project

```bash
git clone <your-repo-url>
cd terminal-app-template
```

### 2. Set Up Virtual Environment

**Option A: Using `uv` (Recommended - Faster)**

```bash
# Install uv if you don't have it: https://github.com/astral-sh/uv#installation
# macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
uv pip install typer rich pynput pyautogui pyperclip requests Pillow python-daemon toml flake8 pytest pyinstaller
```

**Option B: Using Standard Python**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
pip install typer rich pynput pyautogui pyperclip requests Pillow python-daemon toml flake8 pytest pyinstaller
```

### 3. Verify Installation

```bash
# Check if all dependencies are installed
pip list

# Test the CLI
python -m app.cli --help
```

You should see the application help menu with available commands.

### 4. Run Your First Action

```bash
# Test an action directly
python -m app.cli action screenshot.full

# This will show a placeholder message about taking a screenshot
```

### 5. Success! 🎉

If you see output like this, everything is working:

```
INFO: Loading local configuration overrides from /path/to/config.local.toml
INFO: Attempting to run action: screenshot.full
INFO: Loading actions...
INFO: Discovered action: registry.load_action_registry
INFO: Discovered action: screenshot.full
Executing action: screenshot.full
...
INFO: Action 'screenshot.full' executed successfully.
```

## Development Workflow

### Running the Application

**View all available commands:**
```bash
python -m app.cli --help
```

**Run individual actions:**
```bash
# Take a screenshot (placeholder implementation)
python -m app.cli action screenshot.full

# View current configuration
python -m app.cli config show
```

**Start the full application with shortcuts (requires GUI environment):**
```bash
# Normal mode with global shortcuts
python -m app.cli run

# Safe mode without shortcuts (useful for testing)
python -m app.cli run --safe-mode
```

⚠️ **Note**: The `run` command starts global keyboard shortcuts that listen system-wide. Use `Ctrl+C` to stop.

### Running Tests

```bash
# Run all tests
python -m pytest

# Run tests with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_config.py -v
```

**Current test coverage:** 34 tests covering CLI, configuration, actions, and shortcuts.

### Development and Testing Cycle

1. **Make changes** to code in `app/` directory
2. **Test manually** with `python -m app.cli action <action-name>`
3. **Run tests** with `python -m pytest`
4. **Test CLI** with `python -m app.cli --help`

## Building Standalone Executable

### Quick Build (Recommended)

```bash
# Use the provided build script (handles code signing automatically)
./scripts/build.sh
```

### Manual PyInstaller Build

```bash
# Install PyInstaller (if not already installed)
pip install pyinstaller

# Quick build (single command)
pyinstaller --onefile --name aio_terminal_template --add-data "config.toml:." app/cli.py

# Advanced build (using spec file for better control and reproducibility)
pyinstaller aio_terminal_template.spec

# Test the built executable
./dist/aio_terminal_template --help
```

### Code Signing for macOS

**For distribution without security warnings:**

```bash
# Use the signing-aware build script
python scripts/build_signed.py

# Or build without signing if no certificate available
python scripts/build_signed.py --no-sign
```

**Requirements for code signing:**
- Apple Developer account ($99/year)
- Developer ID Application certificate installed in Keychain
- Entitlements file (provided: `entitlements.plist`)

**Benefits:**
- ✅ **Industry standard** - Most popular Python packaging tool
- ✅ **Zero configuration** - Auto-detects dependencies
- ✅ **Single file output** - ~16MB executable
- ✅ **Cross-platform** - Works on Linux, macOS, and Windows
- ✅ **Zero dependencies** - Target machines don't need Python installed
- ✅ **Code signing support** - Eliminates macOS security warnings

### Build Output Structure

```
dist/
└── aio_terminal_template # Single executable file (~16MB)
```

## Project Structure

```
terminal-app-template/
├── app/                 # Main application code
│   ├── cli.py          # CLI entry point
│   ├── actions/        # Action modules (screenshot, etc.)
│   ├── shortcuts/      # Global shortcut manager
│   ├── core/           # Core functionality (config, etc.)
│   └── viewer/         # UI components (placeholder)
├── tests/              # Test suite
├── dist/               # PyInstaller build output
├── config.toml         # Default configuration
├── config.local.toml   # Local overrides (optional)
├── aio_terminal_template.spec # PyInstaller configuration
└── docs/               # Documentation
```

## Configuration

The app uses TOML configuration files:

- **`config.toml`**: Default settings
- **`config.local.toml`**: Local overrides (gitignored)

Example configuration:
```toml
[paths]
screenshots_folder = "~/screenshots"

[shortcuts.screenshot_full]
enabled = true
keys = "cmd+shift+s"
action = "screenshot.full"
```

## Adding New Actions

1. **Create action file** in `app/actions/`:
```python
def my_action(config):
    """My custom action"""
    print("Executing my action!")
    return "Success"
```

2. **Test the action**:
```bash
python -m app.cli action my_action
```

Actions are automatically discovered by the registry system.

## Troubleshooting

**Virtual environment issues:**
```bash
# Deactivate and recreate
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install typer rich pynput pyautogui pyperclip requests Pillow python-daemon toml flake8 pytest pyinstaller
```

**Permission issues on macOS:**
The app may need accessibility permissions for global shortcuts. Go to System Preferences > Security & Privacy > Privacy > Accessibility and add your terminal app.

**Security warnings on macOS:**
If you see "Apple could not verify [app] is free of malware", you have several options:
1. **Use code signing** (recommended): Run `./scripts/build.sh` with a Developer ID certificate
2. **Override security warning**: Right-click the app → "Open" → "Open" in the dialog
3. **Disable Gatekeeper temporarily**: `sudo spctl --master-disable` (not recommended)

**Build issues:**
```bash
# Clean build and retry
rm -rf build/ dist/
pyinstaller aio_terminal_template.spec

# Or use the build script
./scripts/build.sh
```

**Important Notes:**
- Make sure your virtual environment is activated before building
- The build process includes all dependencies, so the final executable is self-contained
- Use the spec file for reproducible builds
- For distribution, code signing eliminates security warnings

## PyInstaller Best Practices

**Recommended Build Configuration:**
```bash
# Use the spec file for consistent, reproducible builds
pyinstaller aio_terminal_template.spec

# Or use command line for quick builds
pyinstaller --onefile --name aio_terminal_template --add-data "config.toml:." app/cli.py
```

**Optimization Tips:**
- Use the spec file for advanced configuration and reproducible builds
- Include necessary data files with `--add-data` or in the spec file
- Test the built executable on target machines before distribution
- Consider using `--upx` for smaller file sizes (if UPX is installed)

**Cross-Platform Building:**
- Build on each target platform for best compatibility
- Linux builds work on most Linux distributions
- macOS builds require macOS to build
- Windows builds require Windows to build
