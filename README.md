# Meetscribe

[![CI](https://github.com/madpin/Meetscribe2/workflows/CI/badge.svg)](https://github.com/madpin/Meetscribe2/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Meetscribe is a tool that automatically converts audio recordings of meetings into structured, actionable notes. It streamlines the note-taking process by using AI to transcribe speech and enrich the output with relevant context from your work applications.

## ✨ Features

- **🤖 Automated Transcription and Summarization:** Turn raw audio into polished notes without lifting a finger. The tool intelligently processes recordings to create a full transcript, a high-level **summary**, a list of **key decisions**, clear **action items**, and a **speaker timeline** with diarization.
- **🧠 LLM Post-Processing Notes:** Generate three types of AI-enhanced meeting notes (Q=Executive Summary, W=Holistic Analysis, E=Actionable Tasks) using LangChain and OpenAI-compatible APIs. Toggle modes interactively or specify via CLI.
- **📁 Effortless Batch Processing:** Simply point the tool to a folder of your meeting recordings. It automatically finds and processes all supported audio files in one go, saving you the tedious task of handling them one by one.
- **🎯 Interactive Single-File Selection:** Use arrow keys and space bar to interactively choose which file to process from a directory, with live preview of file metadata including size, duration, done status, and relative timestamps. Supports pagination with left/right arrows and configurable page sizes.
- **🖥️ Simple Command-Line Operation:** Designed for efficiency, Meetscribe operates through a clean and simple command-line interface. It provides a fast, scriptable way to manage your meeting notes directly from the terminal.
- **🔄 Smart Skip Reprocessing:** By default, skips processing audio files when output already exists to save time and API costs. Use `--reprocess` flag to force overwriting existing outputs. In `--select` mode, files are reprocessed by default unless explicitly disabled.
- **📋 Newest-First Ordering:** All file lists are automatically sorted by last modified time (newest first) for better UX.
- **🛡️ Safe Batch Processing:** Configurable soft and hard limits prevent accidental large batch runs with user confirmation prompts.
- **📦 Standalone Application:** Packaged as a single, standalone binary file, so you can distribute it as a self-contained application that runs on its own without requiring users to install Python or any other dependencies.
- **📅 Google Calendar Integration:** List past calendar events with attendees, descriptions, and attachment names directly from your terminal.
- **🔗 Calendar-to-File Auto-Linking:** Automatically match audio files to Google Calendar events by modification time, rename outputs to YYYY-MM-DD_Title format, and include event metadata in notes. Events must start before file modification time to ensure logical matching.

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
├── services/
│   ├── llm_notes.py   # LLM-powered note generation (Q/W/E modes)
│   └── agents.py      # Future agent-based implementations
└── cli.py             # Typer-based command-line interface
```

## 🧠 LLM Post-Processing

Meetscribe supports AI-powered post-processing of meeting transcripts to generate three types of structured notes:

- **Q (Executive Summary)**: Clear, concise overview with key points, decisions, risks, and next steps
- **W (Holistic Analysis)**: Comprehensive analysis of themes, participant sentiments, alignment/tension points, and overall tone
- **E (Actionable Tasks)**: Precise list of tasks with assignees, due dates, and descriptions

### Configuration

Add LLM settings to your `config.toml`:

```toml
[llm]
enabled = true
dialect = "openai"
base_url = ""  # Your LiteLLM proxy URL (optional)
api_key = ""   # Set in config.local.toml (never commit!)
model = "gpt-4o-mini"
temperature = 0.2
default_modes = ""  # Default is none. Set to "Q", "WE", or "QWE" to preselect modes.

[llm.prompts]
q = "Write a clear, concise executive summary..."
w = "Provide a holistic analysis of the meeting..."
e = "Extract a precise, actionable list of tasks..."

[llm.paths]
q_output_folder = ""  # Empty/unset = use main output folder
w_output_folder = ""
e_output_folder = ""

[llm.keys]
q = "Q"
w = "W"
e = "E"
```

### Usage Examples

```bash
# Enable LLM and specify modes (no modes preselected by default)
python -m app.cli process dir /path/to/audio --llm --notes QW

# Enable LLM with all modes
python -m app.cli process dir /path/to/audio --llm --notes QWE

# Interactive mode with tri-state mode indicators (✓ processed, o queued, - off)
python -m app.cli process dir /path/to/audio --select

# Process single file with specific modes
python -m app.cli process file meeting.wav --llm --notes E

# Generate LLM notes from existing transcriptions (skip transcription)
python -m app.cli process dir /path/to/audio --llm --notes QWE  # Uses existing .txt files

# Regenerate LLM notes from existing transcriptions (skip audio transcription)
python -m app.cli process dir /path/to/audio --llm --reprocess

# Force complete reprocessing including audio transcription
# (if you want to re-run transcription + regenerate LLM notes)
python -m app.cli process dir /path/to/audio --llm --reprocess  # Uses existing .txt files when available

# Auto-link files to calendar events and rename outputs
python -m app.cli process dir /path/to/audio --link-calendar

# Interactive calendar event selection (Ctrl+C or '0' to skip processing file)
python -m app.cli process dir /path/to/audio --link-calendar --select-calendar-event

# Combine calendar linking with LLM processing
python -m app.cli process dir /path/to/audio --link-calendar --llm --notes QWE

# Process single file with calendar linking
python -m app.cli process file meeting.wav --link-calendar --llm --notes Q
```

## 🚀 Quick Usage

```bash
# Process all files in a directory
python -m app.cli process dir /path/to/audio/files

# Interactive single-file selection
python -m app.cli process dir /path/to/audio/files --select

# List files with metadata
python -m app.cli process list /path/to/audio/files

# Process a single file
python -m app.cli process file /path/to/audio.wav
```

## 📅 Google Calendar Integration

Meetscribe now includes Google Calendar integration to list past events with attendees, descriptions, and attachment names.

### Quick Usage

```bash
# List past calendar events (last 7 days by default)
python -m app.cli calendar past

# List past 3 days of events
python -m app.cli calendar past --days 3

# List up to 20 events
python -m app.cli calendar past --limit 20

# Use specific calendar ID
python -m app.cli calendar past --calendar-id your-calendar-id@group.calendar.google.com

# Show all events (including solo events)
python -m app.cli calendar past --no-group-only
```

### Setup

1. **Get Google Credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the `credentials.json` file

2. **Configure Meetscribe:**
   - Place `credentials.json` at `~/.meetscribe/google/credentials.json` (default)
   - Or set a custom path in `config.local.toml`:
     ```toml
     [google]
     credentials_file = "/path/to/your/credentials.json"
     ```

3. **First Run:**
   - Run `python -m app.cli calendar past`
   - Your browser will open for OAuth consent
   - Token will be saved for future runs

### Output

The command displays a Rich-formatted table with:
- **Start (Local)**: Event start time in your local timezone
- **Title**: Event title/summary
- **Attendees**: List of attendee names or emails (Indeed emails show only username)
- **Description**: Event description (truncated if long)
- **Attachments**: Names of attached files

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
