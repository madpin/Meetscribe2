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

## 🧠 Smart LLM Processing

Meetscribe intelligently optimizes processing based on existing files:

- **New audio files**: Full transcription + LLM note generation
- **Existing transcriptions + LLM enabled**: Skip transcription, generate LLM notes from existing content
- **Existing transcriptions + LLM enabled + `--reprocess`**: Read existing transcription, regenerate only LLM notes (fast!)
- **Existing transcriptions + no LLM**: Skip file entirely
- **With `--reprocess` on new files**: Force complete transcription + LLM generation

This means you can efficiently experiment with different LLM note types on existing transcriptions without re-running expensive transcription processes!

## 🎯 What Works Now

### ✅ Working Features
- **Audio Processing:** Converts audio recordings into structured meeting notes
- **Batch Processing:** Process entire directories of audio files automatically
- **LLM Post-Processing:** Generate AI-enhanced notes in three modes (Q=Executive Summary, W=Holistic Analysis, E=Actionable Tasks)
- **CLI Interface:** Full command-line interface with audio processing commands
- **Configuration System:** TOML-based configuration with local overrides
- **Deepgram Integration:** AI-powered transcription and analysis

### ⌨️ Available Commands

```bash
# Process audio files from a directory (skips existing outputs by default)
python -m app.cli process dir /path/to/audio/files

# Force reprocessing of all files, even if outputs exist
python -m app.cli process dir /path/to/audio/files --reprocess

# Interactive single-file selection from a directory
python -m app.cli process dir /path/to/audio/files --select

# List audio files in a directory with metadata (filename, size, duration, etc.)
python -m app.cli process list /path/to/audio/files

# Process a single audio file directly
python -m app.cli process file /path/to/audio.wav
python -m app.cli process file /path/to/audio.wav --reprocess

# LLM Post-Processing Examples
# Enable LLM and specify modes (no modes preselected by default)
python -m app.cli process dir /path/to/audio/files --llm --notes QW

# Enable LLM with all modes (Q=Executive Summary, W=Holistic Analysis, E=Actionable Tasks)
python -m app.cli process dir /path/to/audio/files --llm --notes QWE

# Interactive selection with tri-state mode indicators (✓ processed, o queued, - off)
python -m app.cli process dir /path/to/audio/files --select

# Process single file with LLM (E=Actionable Tasks only)
python -m app.cli process file /path/to/audio.wav --llm --notes E

# Generate LLM notes from existing transcriptions (skip expensive transcription)
python -m app.cli process dir /path/to/audio/files --llm --notes QWE  # Uses existing .txt files

# Force reprocessing of both transcription and LLM notes
python -m app.cli process dir /path/to/audio/files --llm --reprocess

# View available commands
python -m app.cli --help
```

#### Interactive Selection Controls
When using `--select`, navigate with:
- **↑/↓ arrows**: Move selection highlight within current page
- **←/→ arrows**: Navigate between pages (wraps around)
- **Space**: Toggle selection of highlighted file (supports multiple selections across pages)
- **Q/W/E keys**: Toggle LLM note generation modes for the current file (Q=Executive Summary, W=Holistic Analysis, E=Actionable Tasks)
- **Enter**: Confirm selection (processes all selected files, or highlighted file if none selected)
- **Esc**: Cancel selection

The interface shows page information and includes:
- **Pagination**: Shows "Page X/Y — Showing A-B of N — ✓ processed, o queued, - off" in the title
- **Page size**: Configurable via `[ui].selection_page_size` (default: 10)
- **Done status**: ✓ indicates files that have already been processed (output .txt exists)
- **Mode status**: Tri-state indicators for each LLM mode:
  - **✓**: Mode file already exists (previously processed)
  - **o**: Mode is queued for processing (selected but not yet processed)
  - **-**: Mode is not selected
- **Relative timestamps**: Modified dates show both absolute time and relative age (e.g., "2024-01-15 14:30 (2h)")
- **Newest first**: Files are automatically sorted by last modified time
- **Lazy loading**: Duration is computed only for visible page items for better performance
- **Default reprocess**: Selected files are reprocessed by default (overwrites existing outputs) unless `--reprocess=false` is explicitly specified

## ⚙️ Configuration

**⚠️ SECURITY WARNING:** Never commit API keys to version control. Always use `config.local.toml` for sensitive configuration.

**Configuration is validated at startup via Pydantic models for type safety and consistency.**

Create `config.local.toml` in the project root (it's already in `.gitignore`):

```toml
[deepgram]
api_key = "your_deepgram_api_key_here"

[paths]
output_folder = "~/Documents/Meetscribe"

[ui]
selection_page_size = 10  # Items per page in --select mode

[processing]
soft_limit_files = 10     # Prompt for confirmation above this count
hard_limit_files = 25     # Abort processing above this count
```

The app automatically merges `config.local.toml` over `config.toml`, keeping your API key secure.

#### Google Calendar Integration (Optional)

Meetscribe includes Google Calendar integration for listing past events:

```bash
# Install Google API dependencies
pip install google-api-python-client google-auth google-auth-oauthlib

# Configure Google Calendar (optional)
echo '[google]
credentials_file = "~/.meetscribe/google/credentials.json"
token_file = "~/.meetscribe/google/token.json"
default_past_days = 7
max_results = 50
filter_group_events_only = true' >> config.local.toml

# List past calendar events
python -m app.cli calendar past

# Auto-link files to calendar events
python -m app.cli process dir /path/to/audio --link-calendar

# Interactive calendar event selection
python -m app.cli process dir /path/to/audio --link-calendar --select-calendar-event

# Combine calendar linking with LLM processing
python -m app.cli process dir /path/to/audio --link-calendar --llm --notes QWE
```

**Setup Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Calendar API
3. Create OAuth Desktop credentials
4. Download `credentials.json` to `~/.meetscribe/google/credentials.json`
5. Run `python -m app.cli calendar past` for first-time OAuth

#### Calendar-to-File Auto-Linking

Meetscribe can automatically match audio files to Google Calendar events based on file modification time and rename outputs to include event information:

```bash
# Process files with calendar linking enabled
python -m app.cli process dir /path/to/audio --link-calendar

# Combine with LLM processing for enhanced notes
python -m app.cli process dir /path/to/audio --link-calendar --llm --notes QWE

# Single file with calendar linking
python -m app.cli process file meeting.wav --link-calendar
```

**How it works:**
- Files are matched to the closest calendar event within a configurable tolerance window (default: 90 minutes)
- **Event must start BEFORE the file's modification time** (ensures recordings match past meetings)
- **Interactive selection**: Use `--select-calendar-event` to manually choose from available events
- Matched files are renamed from `original_name.txt` to `YYYY-MM-DD_Event_Title.txt`
- Event metadata (title, time, attendees, attachments, description) is prepended to the notes
- LLM outputs use the new naming pattern (e.g., `2024-01-15_Team_Meeting.Q.txt`)

**Interactive Event Selection:**
When using `--select-calendar-event`, you'll see an interactive prompt to choose which calendar event to link to (even if only one event is found):

```
📅 One calendar event found for meeting_audio.wav
Please select which event to link to:
────────────────────────────────────────────────────────────
1. Team Standup Meeting
   Attendees: 5
   Time: 2024-09-08 10:00
────────────────────────────────────────────────────────────
0. Skip - Don't link this file to any event

Enter your choice (1 to link to this event, or 0 to skip):
```

**Or for multiple events:**
```
📅 3 calendar events found for meeting_audio.wav
Please select which event to link to:
────────────────────────────────────────────────────────────
1. Team Standup Meeting
   Attendees: 5
   Time: 2024-09-08 10:00

2. Project Review
   Attendees: 3
   Time: 2024-09-08 11:30

3. Client Call
   Attendees: 2
   Time: 2024-09-08 14:00
────────────────────────────────────────────────────────────
0. Skip - Don't link this file to any event

Enter your choice (1-3, or 0 to skip):
```

**Configuration:**
```toml
[google]
match_tolerance_minutes = 90  # How close file time must be to event time (in minutes)
```

**Output Example:**
```txt
## Linked Calendar Event

**Title:** Team Standup Meeting
**When:** 2024-01-15 10:00 — 10:30
**Attendees:** alice@company.com, bob@company.com, charlie@company.com
**Attachments:** agenda.pdf, meeting_notes.docx
**Event Link:** https://calendar.google.com/event?eid=...
**Source Audio:** team_standup_20240115.wav
**Calendar:** primary

**Description:**
Weekly team standup to discuss project progress and blockers.

---

[Transcription content follows...]
```

#### New Configuration Options

- **`[ui].selection_page_size`** (default: 10): Number of files shown per page in interactive selection
- **`[processing].soft_limit_files`** (default: 10): Show confirmation prompt when processing more files than this
- **`[processing].hard_limit_files`** (default: 25): Abort with error when attempting to process more files than this
- **`[google].filter_group_events_only`** (default: true): Only show events with 2 or more attendees
- **`[google].match_tolerance_minutes`** (default: 90): Time tolerance in minutes for matching audio files to calendar events

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
