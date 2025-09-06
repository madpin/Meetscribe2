# Meetscribe

[![CI](https://github.com/madpin/Meetscribe2/workflows/CI/badge.svg)](https://github.com/madpin/Meetscribe2/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Meetscribe is a tool that automatically converts audio recordings of meetings into structured, actionable notes. It streamlines the note-taking process by using AI to transcribe speech and enrich the output with relevant context from your work applications.

## ✨ Features

- **🤖 Automated Transcription and Summarization:** Turn raw audio into polished notes without lifting a finger. The tool intelligently processes recordings to create a full transcript, a high-level **summary**, a list of **key decisions**, clear **action items**, and a **speaker timeline** with diarization.
- **📁 Effortless Batch Processing:** Simply point the tool to a folder of your meeting recordings. It automatically finds and processes all supported audio files in one go, saving you the tedious task of handling them one by one.
- **🖥️ Simple Command-Line Operation:** Designed for efficiency, Meetscribe operates through a clean and simple command-line interface. It provides a fast, scriptable way to manage your meeting notes directly from the terminal.
- **🔄 Smart Skip Reprocessing:** By default, skips processing audio files when output already exists to save time and API costs. Use `--reprocess` flag to force overwriting existing outputs.
- **📦 Standalone Application:** Packaged as a single, standalone binary file, so you can distribute it as a self-contained application that runs on its own without requiring users to install Python or any other dependencies.

## 🏗️ Architecture Overview

This project is built on a modern, dependency-injected architecture that emphasizes testability, maintainability, and type safety.

### Core Components

```
app/
├── core/
│   ├── context.py      # AppContext - central state management
│   ├── logging.py      # Structured logging setup
│   ├── config.py       # TOML configuration loading
│   └── exceptions.py   # Custom exception classes
├── transcriber.py     # Deepgram transcription and analysis
└── cli.py             # Typer-based command-line interface
```

## 🚀 Getting Started

### 🛠️ For Developers

For instructions on how to set up a development environment, build the project, and contribute, please see the [Developer Guide](./DEVELOPER.md).

## 🚀 Build Method

**PyInstaller** creates a single executable file that works across Linux, macOS, and Windows:

```bash
# Build the executable
pyinstaller meetscribe.spec

# Test the built executable
./dist/meetscribe --help
```

**Note:** The `meetscribe.spec` file bundles `config.toml` with the executable, so users don't need to install configuration files separately.

**Benefits:**
- ✅ **Single file** - Easy to distribute
- ✅ **Cross-platform** - Works on Linux, macOS, and Windows
- ✅ **Zero dependencies** - No Python installation required
- ✅ **Industry standard** - Most popular Python packaging tool
