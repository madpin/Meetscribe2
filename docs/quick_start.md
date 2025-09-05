# Quick Start Guide

Welcome to the AIO Terminal Template! This guide will help you get started with building and using your own terminal application.

## 🚀 Quick Development Setup

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd terminal-app-template

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install typer rich pynput pyautogui pyperclip requests Pillow python-daemon toml flake8 pytest pyinstaller
```

### 2. Test the Application

```bash
# Test CLI
python -m app.cli --help

# Test screenshot action (implemented)
python -m app.cli action screenshot.full

# View configuration
python -m app.cli config show
```

### 3. Build Standalone Executable

```bash
# Build with PyInstaller
pyinstaller --onefile --name aio_terminal_template --add-data "config.toml:." app/cli.py

# Test the built executable
./dist/aio_terminal_template --help
```

The executable will be created in the `dist/` directory and can be distributed to any machine (Linux, macOS, or Windows) without requiring Python to be installed.

## 🔄 Updating Your Application

### For End Users (Using Built Executable)
If you have a pre-built executable, you can update it automatically:

```bash
# Check for new versions
./{{PROJECT_NAME}} update check

# Download and install the latest version
./{{PROJECT_NAME}} update now
```

**Keyboard shortcuts:**
- `Ctrl+Shift+U`: Check for updates
- `Ctrl+Shift+D`: Auto-update to latest version

The update process automatically creates a backup of your current executable and safely replaces it with the new version.

### For Developers
When running from source, update normally:
```bash
git pull
pip install -e .
```

## 🎯 What Works Now

### ✅ Working Features
- **Screenshot Action:** Captures full-screen screenshots and copies path to clipboard
- **CLI Interface:** Full command-line interface with action execution
- **Configuration System:** TOML-based configuration with local overrides
- **Action Registry:** Automatically discovers and loads action modules

### ⌨️ Available Commands

```bash
# Run actions directly
python -m app.cli action screenshot.full

# Start with global shortcuts (framework ready)
python -m app.cli run

# Start without shortcuts (safe mode)
python -m app.cli run --safe-mode

# Manage configuration
python -m app.cli config show
python -m app.cli config edit

# View logs
python -m app.cli logs tail
```

## ⚙️ Configuration

The application's behavior is controlled by `config.toml`. Create `config.local.toml` for local overrides:

```toml
[paths]
screenshots_folder = "~/my_screenshots"

[shortcuts.screenshot_full]
keys = "<ctrl>+<shift>+s"
action = "screenshot.full"
enabled = true
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest -v

# Run specific test file
python -m pytest tests/test_screenshot_action.py -v
```

## 📝 Next Steps

1. **Add More Actions:** Implement clipboard clean, network ping, and update check actions
2. **Build the Live Viewer:** Complete the Rich-based action log viewer
3. **Add GitHub Actions:** Set up CI/CD workflows for automated testing and releases
4. **Customize:** Modify the configuration and add your own actions

For detailed development instructions, see the [Developer Guide](./DEVELOPMENT.md).
