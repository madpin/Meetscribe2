# Meetscribe Developer Testing Guide

## Overview

This comprehensive guide covers testing Meetscribe locally across multiple levels: unit tests with mocks, optional integration tests against Deepgram, end-to-end CLI testing, and build verification.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Quick Start Commands](#quick-start-commands)
- [Configuration](#configuration)
- [Testing Strategies](#testing-strategies)
  - [Unit Testing](#unit-testing)
  - [Integration Testing](#integration-testing)
  - [Manual E2E Testing](#manual-e2e-testing)
  - [Build Smoke Tests](#build-smoke-tests)
- [What to Test](#what-to-test)
- [Troubleshooting](#troubleshooting)
- [Test Structure Guidelines](#test-structure-guidelines)
- [CI/CD Integration](#cicd-integration)
- [Contact Points](#contact-points)

## Prerequisites

- **Python**: 3.10 or higher
- **Operating System**: macOS, Linux, or Windows
- **Version Control**: Git
- **Optional**: Deepgram API key (for integration tests only)

## Environment Setup

### Virtual Environment

Create and activate a virtual environment:

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### Dependencies

Install required packages:

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies
pip install pytest pytest-cov flake8 ruff pyinstaller
```

## Quick Start Commands

### Code Quality
```bash
# Lint code for style and errors
./scripts/run-flake8.sh
```

### Testing
```bash
# Run all unit tests
pytest

# Run tests with coverage report
pytest --cov=app --cov-report=term-missing

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_config.py -v
```

### Build Testing
```bash
# Build executable
./scripts/build.sh

# Test built executable
./dist/meetscribe --help
```

## Configuration

### Configuration Files

Meetscribe uses a hierarchical configuration system:

- **Base config**: `config.toml` (committed to repository)
- **Local overrides**: `config.local.toml` (local, uncommitted)

The configuration system performs deep merging, allowing local overrides to customize any setting.

### API Keys and Security

**🚨 CRITICAL SECURITY WARNING:** Never commit API keys or `config.local.toml` to version control. This is a common security mistake that can lead to unauthorized API usage and costs.

#### For Unit Testing
- Use mocked services instead of real API keys
- All network calls should be mocked to ensure fast, reliable tests

#### For Integration Testing
Create `config.local.toml` in the project root:

```toml
[deepgram]
api_key = "YOUR_DEEPGRAM_API_KEY"
```

**Important:** Add `config.local.toml` to your `.gitignore` or ensure it's never staged.

## Security Best Practices

### API Key Management
**🚨 CRITICAL:** Never commit API keys or sensitive configuration to version control.

#### Safe Configuration Setup
1. **Use `config.local.toml`** for all sensitive settings
2. **Verify `.gitignore`** includes `config.local.toml`
3. **Review diffs** before committing to ensure no secrets are included
4. **Use environment variables** for CI/CD pipelines when possible

#### Development vs Production
- **Development**: Use `config.local.toml` with test API keys
- **CI/CD**: Use encrypted secrets and environment variables
- **Production**: Never store keys in files; use secure key management

### Code Security
- **Dependencies**: Keep all packages updated and audit for vulnerabilities
- **Input Validation**: Validate all user inputs and file paths
- **Error Handling**: Don't expose sensitive information in error messages
- **Logging**: Be cautious about logging sensitive data

### Network Security
- **HTTPS Only**: All external API calls use secure connections
- **Data Transmission**: Audio files are sent encrypted to Deepgram
- **API Keys**: Transmitted securely in HTTP headers

## CLI Reference

### Available Commands

Meetscribe currently provides one main command:

```bash
python -m app.cli process dir <audio_directory>
```

**Parameters:**
- `audio_directory`: Path to directory containing audio files (required)

**Supported Audio Formats:**
- `.wav` (audio/wav)
- `.mp3` (audio/mpeg)
- `.m4a` (audio/mp4)
- `.aac` (audio/aac)

**Behavior:**
- Non-recursive directory scan
- Processes all supported audio files in the specified directory
- Creates `<stem>.txt` output files in the configured output folder
- Exit code 1 if path is not a directory
- Exit code 0 for success (even if no files found)

**Example:**
```bash
python -m app.cli process dir /path/to/meetings
```

## Testing Strategies

### Unit Testing

**Goal:** Validate application logic without making network calls to external services.

#### What to Test

Core functionality that should be covered by unit tests:

- **Configuration** (`app/core/config.py`):
  - `deep_merge()` function behavior
  - `load_config()` with and without local overrides
- **Logging** (`app/core/logging.py`):
  - `setup_logging()` creates proper Rich and file handlers
  - Log level configuration
- **Utilities** (`app/core/utils.py`):
  - `ensure_directory_exists()`
  - `safe_path_join()`
- **Transcriber** (`app/transcriber.py`):
  - `_format_results()` with various response formats
  - Error handling in transcription logic
- **CLI** (`app/cli.py`):
  - `process dir` command with missing directories
  - `process dir` command with empty directories

#### Mocking Deepgram

The `Transcriber` expects Deepgram responses with this structure:

```python
# Mock response structure
response.results = types.SimpleNamespace()
response.results.summary = types.SimpleNamespace(short="Meeting summary...")
response.results.channels = [types.SimpleNamespace()]
response.results.channels[0].alternatives = [types.SimpleNamespace(transcript="Full transcript...")]
response.results.topics = types.SimpleNamespace(segments=[types.SimpleNamespace(topic="Topic 1")])
response.results.intents = types.SimpleNamespace(segments=[types.SimpleNamespace(intents=[types.SimpleNamespace(intent="Action item")])])
```

**Mocking Strategies:**
- Create fake objects using `types.SimpleNamespace`
- Monkeypatch `DeepgramClient` in tests
- Use dependency injection where possible

#### Test Assertions

**Success Cases:**
- ✅ Summary appears on first line(s)
- ✅ Topics and action items as bullet lists
- ✅ Transcript after `---` separator

**Edge Cases:**
- 📝 Missing fields fallback to "No summary available"
- 📝 Empty lists show "- None"
- ❌ Error handling returns "Error: Could not format the results"

**CLI Behavior:**
- Exit code 1 for non-existent directories
- "No supported audio files found" for empty directories

#### Example Test Case

```python
import pytest
from unittest.mock import patch, MagicMock
import types
from app.transcriber import Transcriber

def test_format_results_with_complete_response():
    # Setup fake response
    fake_response = types.SimpleNamespace()
    fake_response.results = types.SimpleNamespace()
    fake_response.results.summary = types.SimpleNamespace(short="Meeting about Q4 planning")
    fake_response.results.channels = [types.SimpleNamespace()]
    fake_response.results.channels[0].alternatives = [types.SimpleNamespace(transcript="Full meeting transcript...")]
    fake_response.results.topics = types.SimpleNamespace(segments=[types.SimpleNamespace(topic="Q4 Goals")])
    fake_response.results.intents = types.SimpleNamespace(segments=[types.SimpleNamespace(intents=[types.SimpleNamespace(intent="Schedule follow-up")])])

    # Create transcriber and test
    transcriber = Transcriber()
    result = transcriber._format_results(fake_response.results)

    # Assertions
    assert "Meeting about Q4 planning" in result
    assert "- Q4 Goals" in result
    assert "- Schedule follow-up" in result
    assert "---" in result
    assert "Full meeting transcript..." in result
```

### Integration Testing

**⚠️ Note:** Only run these tests when you explicitly want to validate end-to-end transcription with real API calls.

#### Preparation

1. **Audio Files**: Use small, short-duration WAV files to minimize costs and test time
2. **API Key**: Set up `config.local.toml` with your Deepgram key
3. **File Format**: Use supported audio formats (.wav, .mp3, .m4a, .aac) - MIME types are automatically detected

#### Test Steps

1. **Setup Test Directory:**
   ```bash
   mkdir -p sample_audio
   # Place a short demo.wav file in sample_audio/
   ```

2. **Run Integration Test:**
   ```bash
   python -m app.cli process dir sample_audio
   ```

3. **Verify Results:**
   - ✅ Console shows "Processing demo.wav..."
   - ✅ Output file `demo.txt` created in output directory
   - ✅ Notes file contains:
     - Meeting summary
     - Key decisions and action items (may be empty)
     - Full transcript after `---` separator

#### Log Verification

Check application logs for detailed information:
```bash
tail -n 200 ~/.meetscribe/meetscribe.log
```

### Manual E2E Testing

For comprehensive CLI testing without real API calls:

#### Setup
- Temporarily inject a fake Deepgram client
- Use monkeypatching to bypass network calls
- Run unit tests that exercise full CLI workflows

#### Verification Points
- ✅ CLI argument parsing and validation
- ✅ Output directory creation
- ✅ File writing operations
- ✅ Log file generation and content
- ✅ Error handling and user feedback

### Build Smoke Tests

**Goal:** Validate that the packaged executable works correctly.

#### Build Process
```bash
# Build the executable
./scripts/build.sh
```

#### Verification
```bash
# Test basic CLI functionality
./dist/meetscribe --help
```

#### macOS Specific
For unsigned builds, macOS may show security warnings. For local development:

```bash
# Remove quarantine (development only)
./scripts/fix_macos_security.sh dist/meetscribe
```

**Purpose:** Ensures the executable starts and CLI entry points function correctly.

## What to Test

### Core Functionality

#### Configuration & Logging
- ✅ `load_config()` merges `config.toml` and `config.local.toml`
- ✅ `AppContext` creates `~/.meetscribe/meetscribe.log`
- ✅ Application startup logging works correctly

#### Transcriber Logic
- ✅ Summary, topics, intents, and transcript formatting
- ✅ Graceful handling of missing response fields
- ✅ Error logging and user-friendly error messages
- ✅ Exception handling in transcription pipeline

#### CLI Commands
- ✅ `process dir` handles missing directories (exit code 1)
- ✅ `process dir` handles empty directories
- ✅ Only processes supported file extensions (.wav, .mp3, .m4a, .aac)
- ✅ Creates output directory if it doesn't exist
- ✅ Generates one `.txt` file per audio file
- ✅ Displays "Notes saved to..." confirmation

## Troubleshooting

### Common Issues and Solutions

#### 🔑 Missing Deepgram API Key
**Error:** "Deepgram API key not found in config.toml"

**Solutions:**
- Create `config.local.toml` with your API key
- Run only unit tests with mocks for development

#### 🎵 No Supported Audio Files
**Problem:** Files not being processed

**Check:**
- File extensions must be `.wav`, `.mp3`, `.m4a`, or `.aac`
- For integration tests, prefer `.wav` files (MIME type compatibility)

#### 🍎 macOS Permission Issues
**Problem:** Unsigned executables blocked by macOS

**Solutions:**
- Use Finder to "Open" the executable
- Run `./scripts/fix_macos_security.sh dist/meetscribe` for development

#### 📝 Missing Log Files
**Problem:** `~/.meetscribe/meetscribe.log` not found

**Solution:** Run any CLI command first to initialize the logging system

#### 🔒 Security - Never Commit Secrets
**Critical:** Never commit `config.local.toml` or API keys

**Best Practices:**
- Add `config.local.toml` to `.gitignore`
- Review diffs before pushing
- Use environment variables for CI/CD

## Test Structure Guidelines

When adding new tests, follow this structure:

### Test File Organization

#### `tests/test_config.py`
- `load_config()` with and without local overrides
- `deep_merge()` behavior and edge cases

#### `tests/test_logging.py`
- `setup_logging()` creates Rich and file handlers
- Log level configuration and filtering

#### `tests/test_utils.py`
- `ensure_directory_exists()` functionality
- `safe_path_join()` path manipulation
- `get_timestamp_filename()` timestamp generation

#### `tests/test_transcriber_unit.py`
- `Transcriber._format_results()` with various fake response objects
- `Transcriber.process_audio_file()` with monkeypatched client
- Error handling and edge cases

#### `tests/test_cli_process.py`
- CLI exit codes for invalid/empty directories
- File creation assertions with mocked Transcriber
- Argument parsing and validation

## CI/CD Integration

### Recommended CI Setup

#### Test Matrix
- **Platforms:** Linux, macOS, Windows
- **Python Versions:** 3.10+
- **Tools:** flake8, pytest

#### Integration Tests
- Mark integration tests with `@pytest.mark.integration`
- Only run when `DEEPGRAM_API_KEY` secret is present
- Skip gracefully when API key is unavailable

#### Coverage and Artifacts
- Generate and upload coverage reports
- Build executable artifacts for releases
- Store test results and logs

## Contact Points

### Debugging Resources

#### Logs
- **Application Logs:** `~/.meetscribe/meetscribe.log`
- **CLI Command:** `tail -n 200 ~/.meetscribe/meetscribe.log`

#### Output Locations
- **Notes Folder:** Configured via `[paths] output_folder` in `config.toml`
- **Default Path:** `~/Documents/Meetscribe`

#### Help and Documentation
- **CLI Help:** `python -m app.cli --help`
- **Process Directory:** `python -m app.cli process dir --help`

---

## Summary

This guide provides comprehensive testing coverage for Meetscribe across unit, integration, and end-to-end scenarios. Follow these practices to:

- ✅ Ensure reliable, fast unit tests with proper mocking
- ✅ Validate end-to-end functionality with optional integration tests
- ✅ Maintain build integrity with smoke tests
- 🔒 Keep API keys and secrets secure
- 📊 Generate meaningful test coverage reports

Remember: Always prioritize unit tests for development speed and reliability, using integration tests only when validating real API interactions.