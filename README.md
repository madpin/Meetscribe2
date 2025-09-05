# AIO Terminal Template

[![CI](https://github.com/{{OWNER_NAME}}/{{REPO_NAME}}/workflows/CI/badge.svg)](https://github.com/{{OWNER_NAME}}/{{REPO_NAME}}/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A modern, ready-to-clone project template for building terminal-first applications that bundle into **standalone executables** using PyInstaller.

**📦 No Python Installation Required:** The built executables are completely self-contained and work on any machine without Python installed.

This template provides a solid foundation for creating powerful internal tools, utilities for support engineers, and ops tools that require global keyboard shortcuts, a live action log, and automated releases.

## ⚠️ macOS Security Notice

**Important for macOS Users:** When downloading from GitHub releases, you may see:

> "Apple could not verify 'aio_terminal_template' is free of malware"

**This is normal for unsigned applications.** To run the app:

1. **Right-click** the downloaded file → **"Open"** → Click **"Open"** again in the dialog
2. macOS will remember your choice and won't show the warning again

**Alternative:** Use the security fix script: `./scripts/fix_macos_security.sh /path/to/downloaded/app`

**For signed builds:** Set up Apple Developer certificates (see [Code Signing Guide](docs/CODE_SIGNING.md))

## ✨ Features

- **🔧 Command-line Framework:** Clean, modern CLI powered by [Typer](https://typer.tiangolo.com/).
- **📊 Live Action Stream:** A read-only log viewer using [Rich](https://rich.readthedocs.io/en/latest/) to show what the app is doing in real-time.
- **⌨️  Global Keyboard Shortcuts:** A `pynput`-based listener to trigger actions from anywhere in the OS.
- **🧩 Action Library:** A modular system for adding new functionality (e.g., screenshots, clipboard manipulation, API calls).
- **📦 PyInstaller Packaging:** Single executable file (~16MB) that works across Linux, macOS, and Windows.
- **🚀 Zero Dependencies:** Built executables run on any machine without Python or dependencies installed.
- **⚙️  Configuration-First:** Behavior, shortcuts, and API endpoints are controlled via a simple `config.toml` file with type-safe dataclass models.
- **🏗️  Dependency Injection:** Clean AppContext architecture for better testability and maintainability.
- **📝 Structured Logging:** Rich-powered logging with configurable levels and beautiful console output.
- **🧪 Well Tested:** Comprehensive test suite demonstrating improved testability with dependency injection.

## 🏗️ Architecture Overview

This template has been refactored to use a modern, dependency-injected architecture that emphasizes testability, maintainability, and type safety.

### Key Architectural Improvements

- **AppContext Pattern:** Centralizes configuration, logging, and action registry management
- **Type-Safe Configuration:** Uses Python dataclasses for configuration models with validation
- **Structured Logging:** Rich-powered logging with configurable levels and beautiful output
- **Dependency Injection:** Components receive their dependencies explicitly rather than accessing global state
- **Enhanced Testability:** Actions can be tested in isolation with mocked dependencies

### Core Components

```
app/
├── core/
│   ├── context.py      # AppContext - central state management
│   ├── models.py       # Type-safe configuration models
│   ├── logging.py      # Structured logging setup
│   ├── config.py       # TOML configuration loading
│   ├── utils.py        # Shared utility functions
│   └── exceptions.py   # Custom exception classes
├── actions/
│   ├── registry.py     # Dynamic action discovery
│   └── *.py           # Individual action implementations
├── shortcuts/
│   └── manager.py     # Global shortcut management
└── cli.py             # Typer-based command-line interface
```

### Action Signature Changes

**Before (Global State):**
```python
def my_action(config):
    # Access global config directly
    print("Action executed")  # Poor logging
```

**After (Dependency Injection):**
```python
def my_action(ctx: AppContext) -> str:
    # Receive dependencies via AppContext
    ctx.logger.info("Action executed")  # Structured logging
    return "Result"
```

## Getting Started

### 🚀 For Users (Using the Built Application)
To get started with using the application, see the [Quick Start guide](./docs/quick_start.md).

### 🛠️ For Developers (Using this Template)
If you're using this as a template for your own project:

- **🚀 Automatic Setup**: Placeholders are automatically replaced when you create a repository from this template
- **📋 Manual Setup**: See the [Template Setup Guide](./TEMPLATE_SETUP.md) for detailed customization instructions
- **✅ Validation**: Run `python scripts/validate_setup.py` to verify everything is configured correctly

For instructions on how to set up a development environment, build the project, and contribute, please see the [Developer Guide](./docs/DEVELOPMENT.md).

## 🔄 Updating the Application

### For Users with Executable-Only Installation

If you downloaded a pre-built executable and want to update to the latest version, you have several options:

#### Option 1: Automatic Update (Recommended)
```bash
# Check for updates
./{{PROJECT_NAME}} update check

# Download and install automatically (creates backup)
./{{PROJECT_NAME}} update now
```

**Or use keyboard shortcuts:**
- `Ctrl+Shift+U`: Check for updates
- `Ctrl+Shift+D`: Download and install latest version

#### Option 2: Manual Download
1. Visit the [GitHub Releases](https://github.com/{{OWNER_NAME}}/{{REPO_NAME}}/releases) page
2. Download the appropriate executable for your platform:
   - **Linux:** `{{PROJECT_NAME}}-linux.tar.gz`
   - **macOS:** `{{PROJECT_NAME}}-macos.tar.gz`
   - **Windows:** `{{PROJECT_NAME}}-windows.zip`
3. Extract the archive and replace your current executable
4. **Important:** Keep a backup of your old executable during manual updates

#### Safety Features
- ✅ **Automatic Backups:** Creates `{executable}.backup` before replacement
- ✅ **Cross-Platform:** Detects your OS and downloads the correct executable
- ✅ **Safe Replacement:** Uses batch files on Windows to avoid file locking issues
- ✅ **Rollback Support:** If update fails, the backup is automatically restored

#### Troubleshooting Updates
- **Permission Errors:** On Unix systems, ensure the executable has proper permissions: `chmod +x {{PROJECT_NAME}}`
- **Windows File Locking:** If direct replacement fails, a batch file is created for delayed replacement
- **Network Issues:** Updates require internet connectivity to download from GitHub
- **Restore from Backup:** If something goes wrong, rename `{executable}.backup` back to the original name

### For Developers
If you're running from source code, update using your package manager:
```bash
# If installed via pip
pip install --upgrade {{PROJECT_NAME}}

# Or from source
git pull && pip install -e .
```

## 🎯 Current Implementation Status

### ✅ Implemented Features
- **CLI Framework:** Full Typer-based command-line interface
- **Screenshot Action:** Working screenshot capture with clipboard integration
- **Configuration System:** TOML-based configuration with local overrides
- **Action Registry:** Dynamic action discovery system
- **Global Shortcuts:** pynput-based shortcut listener (framework ready)
- **Build System:** PyInstaller configuration ready
- **Test Suite:** 34 comprehensive tests covering core functionality

### 🔄 In Development
- **Live Action Viewer:** Rich-based log viewer (framework in place)
- **Additional Actions:** Clipboard clean, network ping, update check
- **GitHub Actions:** ✅ CI/CD workflows implemented for testing and releases

### 📋 Planned Features
- **Enhanced UI:** Full Rich-based interactive viewer
- **More Actions:** File operations, system utilities, API integrations
- **Plugin System:** Extensible action architecture
- **Cross-platform:** Enhanced Windows and Linux support

## 🚀 Build Method

**PyInstaller** creates a single executable file that works across Linux, macOS, and Windows:

```bash
# Build the executable
pyinstaller --onefile --name {{PROJECT_NAME}} --add-data "config.toml:." app/cli.py

# Test the built executable
./dist/{{PROJECT_NAME}} --help
```

**Benefits:**
- ✅ **Single file** (~16MB) - Easy to distribute
- ✅ **Cross-platform** - Works on Linux, macOS, and Windows
- ✅ **Zero dependencies** - No Python installation required
- ✅ **Industry standard** - Most popular Python packaging tool

## 📁 Project Structure

```
terminal-app-template/
├── app/                          # Main application code
│   ├── cli.py                   # CLI entry point (Typer-based)
│   ├── actions/                 # Action modules
│   │   ├── __init__.py
│   │   ├── registry.py          # Action discovery system
│   │   └── screenshot.py        # Screenshot action (implemented)
│   ├── shortcuts/               # Global shortcut manager
│   │   ├── __init__.py
│   │   └── manager.py           # pynput-based shortcut listener
│   ├── core/                    # Core functionality
│   │   ├── __init__.py
│   │   └── config.py            # TOML configuration system
│   └── viewer/                  # Rich-based UI components
│       └── __init__.py
├── tests/                       # Test suite (34 tests)
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_registry.py
│   ├── test_screenshot_action.py
│   └── test_shortcuts.py
├── docs/                        # Documentation
│   ├── DEVELOPMENT.md
│   └── quick_start.md
├── config.toml                  # Default configuration
├── pyproject.toml               # Modern Python packaging
├── aio_terminal_template.spec   # PyInstaller build configuration
└── README.md
```
