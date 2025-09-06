# Quick Start Guide

Welcome to Meetscribe! This guide will help you get started with converting your meeting audio recordings into structured notes.

## 🚀 Quick Development Setup

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd meetscribe

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development (optional)
pip install flake8 pytest pyinstaller
```

### 2. Test the Application

```bash
# Test CLI
python -m app.cli --help

# Test audio processing (replace with your audio folder path)
python -m app.cli process dir /path/to/your/audio/files
```

### 3. Build Standalone Executable

```bash
# Build with PyInstaller
pyinstaller --onefile --name meetscribe --add-data "config.toml:." app/cli.py

# Test the built executable
./dist/meetscribe --help
```

The executable will be created in the `dist/` directory and can be distributed to any machine (Linux, macOS, or Windows) without requiring Python to be installed.

## 🎯 What Works Now

### ✅ Working Features
- **Audio Processing:** Converts audio recordings into structured meeting notes
- **Batch Processing:** Process entire directories of audio files automatically
- **CLI Interface:** Full command-line interface with audio processing commands
- **Configuration System:** TOML-based configuration with local overrides
- **Deepgram Integration:** AI-powered transcription and analysis

### ⌨️ Available Commands

```bash
# Process audio files from a directory (skips existing outputs by default)
python -m app.cli process dir /path/to/audio/files

# Force reprocessing of all files, even if outputs exist
python -m app.cli process dir /path/to/audio/files --reprocess

# View available commands
python -m app.cli --help
```

## ⚙️ Configuration

**⚠️ SECURITY WARNING:** Never commit API keys to version control. Always use `config.local.toml` for sensitive configuration.

Create `config.local.toml` in the project root (it's already in `.gitignore`):

```toml
[deepgram]
api_key = "your_deepgram_api_key_here"

[paths]
output_folder = "~/Documents/Meetscribe"
```

The app automatically merges `config.local.toml` over `config.toml`, keeping your API key secure.

## 🧪 Testing

```bash
# Run all tests
python -m pytest -v

# Run specific test file
python -m pytest tests/test_config.py -v
```

## 📝 Next Steps

1. **Get a Deepgram API Key:** Sign up at [console.deepgram.com](https://console.deepgram.com) for transcription services
2. **Configure Your API Key:** Add it to `config.local.toml` for secure storage
3. **Test with Audio Files:** Process some meeting recordings and review the output
4. **Customize Output Location:** Modify the output folder path in your configuration

For detailed development instructions, see the [Developer Guide](../DEVELOPER.md).
