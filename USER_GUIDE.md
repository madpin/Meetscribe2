# Meetscribe User Guide

## Table of Contents
- [Overview](#overview)
- [What You Need](#what-you-need)
- [Installation and Setup](#installation-and-setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output and Results](#output-and-results)
- [Troubleshooting](#troubleshooting)
- [Privacy and Security](#privacy-and-security)
- [Tips for Best Results](#tips-for-best-results)
- [Getting Help](#getting-help)

## Overview
Meetscribe converts meeting audio recordings into structured notes. It transcribes audio using Deepgram and produces:
- **Summary**: Concise overview of the meeting content
- **Key decisions**: Important topics and decisions discussed
- **Action items**: Tasks, intents, and follow-ups identified
- **Speaker Timeline**: Speaker-labeled conversation timeline (when diarization is available)
- **Full transcript**: Complete word-for-word transcription

## What You Need
- A [Deepgram API key](https://console.deepgram.com) (free tier available)
- Audio files in WAV, MP3, or M4A format (WAV recommended for best compatibility)
- macOS, Windows, or Linux operating system

## Installation and Setup

### Option A: Packaged Executable
1. Download the Meetscribe executable for your platform
2. **macOS First Run**: If macOS warns the app can't be verified:
   - Right-click the executable and select **Open**
   - Click **Open** again in the dialog that appears
   - For local development builds, advanced users can remove quarantine attributes via terminal

3. Verify installation:
   ```bash
   ./meetscribe --help
   ```

### Option B: Run from Source (Python 3.10+)
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify installation:
   ```bash
   python -m app.cli --help
   ```

## Configuration

### API Key Setup

**⚠️ SECURITY WARNING:** Never commit API keys to version control. Always use `config.local.toml` for sensitive configuration.

1. **Create `config.local.toml`** in the project root (it's already in `.gitignore`)
2. Add your Deepgram API key:
   ```toml
   [deepgram]
   api_key = "YOUR_DEEPGRAM_API_KEY"
   ```

**Why `config.local.toml`?**
- It's automatically merged over `config.toml`
- It's ignored by git (won't be accidentally committed)
- Keeps your API key private and secure

### Output Folder (Optional)
- **Default**: `~/Documents/Meetscribe`
- To change, edit `config.toml`:
  ```toml
  [paths]
  output_folder = "/your/preferred/folder"
  ```

### Configuration Reference

#### Required Files
- **`config.toml`**: Base configuration (must exist)
- **`config.local.toml`**: Local overrides (optional, gitignored)

#### Configuration Sections

**`[deepgram]`**
- **`api_key`** (string, required): Your Deepgram API key from [console.deepgram.com](https://console.deepgram.com)
- **`model`** (string, optional): Deepgram model to use (default: `"nova-3"`)
- **`language`** (string, optional): Language code (default: `"en-US"`)
- **`smart_format`** (boolean, optional): Enable punctuation and capitalization (default: `true`)
- **`diarize`** (boolean, optional): Enable speaker diarization (default: `true`)
- **`diarize_speakers`** (integer, optional): Hint for expected number of speakers (default: `0` = unset)
- **`min_speaker_gap`** (float, optional): Minimum gap between speakers in seconds (default: `0.0` = unset)
- **`max_speaker_gap`** (float, optional): Maximum gap between speakers in seconds (default: `0.0` = unset)
- **`summarize`** (string, optional): Summarization model version (default: `"v2"`)
- **`detect_topics`** (boolean, optional): Enable topic detection (default: `true`)
- **`intents`** (boolean, optional): Enable intent analysis (default: `true`)

**`[paths]`**
- **`output_folder`** (string, optional): Directory for generated notes (default: `~/Documents/Meetscribe`)

**`[processing]`**
- **`reprocess`** (boolean, optional): When true, reprocess audio files even if output .txt already exists (overwrite). Default is false, which skips files with existing outputs.
- **`soft_limit_files`** (integer, optional): Show confirmation prompt when attempting to process more files than this in batch mode. Default is 10.
- **`hard_limit_files`** (integer, optional): Abort with error when attempting to process more files than this in batch mode. Default is 25.

**`[ui]`**
- **`selection_page_size`** (integer, optional): Number of files shown per page in interactive selection mode. Default is 10.

**`[google]`**
- **`credentials_file`** (string, optional): Path to Google OAuth credentials file (default: `"~/.meetscribe/google/credentials.json"`)
- **`token_file`** (string, optional): Path where OAuth tokens are stored (default: `"~/.meetscribe/google/token.json"`)
- **`scopes`** (array, optional): OAuth scopes for Google API access (default: `["https://www.googleapis.com/auth/calendar.readonly"]`)
- **`calendar_id`** (string, optional): Google Calendar ID to query (default: `"primary"`)
- **`default_past_days`** (integer, optional): Default number of past days to query (default: `7`)
- **`max_results`** (integer, optional): Default maximum number of events to return (default: `50`)
- **`filter_group_events_only`** (boolean, optional): Only show events with 2 or more attendees (default: `true`)

#### Configuration Loading
1. `config.toml` is loaded first (required)
2. `config.local.toml` is merged over base config if it exists
3. Deep merge preserves nested structure
4. Local config takes precedence over base config
5. Configuration is validated at startup via Pydantic models for type safety and consistency

## Google Calendar Setup

Meetscribe includes Google Calendar integration to list past events with attendees, descriptions, and attachment names.

### Step-by-Step Setup

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Calendar API:
     - Navigate to "APIs & Services" > "Library"
     - Search for "Google Calendar API"
     - Click "Enable"

2. **Create OAuth Credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application" as the application type
   - Download the `credentials.json` file

3. **Configure Meetscribe:**
   - Place the downloaded `credentials.json` file at: `~/.meetscribe/google/credentials.json`
   - Or set a custom path in `config.local.toml`:
     ```toml
     [google]
     credentials_file = "/path/to/your/credentials.json"
     ```

4. **First Run Authentication:**
   - Run: `python -m app.cli calendar past`
   - Your browser will open for OAuth consent
   - Grant the requested permissions
   - The access token will be saved to `~/.meetscribe/google/token.json` for future runs

### Security Notes
- **Never commit `credentials.json` or `token.json` to version control**
- The OAuth scope is limited to read-only calendar access
- Tokens are stored locally and automatically refreshed when needed
- You can revoke access anytime in your Google Account settings

### Usage Examples

```bash
# List past events (last 7 days by default)
python -m app.cli calendar past

# List past 3 days of events
python -m app.cli calendar past --days 3

# List up to 20 events
python -m app.cli calendar past --limit 20

# Use specific calendar
python -m app.cli calendar past --calendar-id your-calendar-id@group.calendar.google.com

# Show all events (including solo events)
python -m app.cli calendar past --no-group-only

# Override configuration defaults
echo '[google]
default_past_days = 14
max_results = 100
filter_group_events_only = false' > config.local.toml
```

### Output Format

The command displays events in a Rich-formatted table with:
- **Start (Local)**: Event start time converted to your local timezone
- **Title**: Event title/summary
- **Attendees**: Comma-separated list of attendee names (prefers display names over email addresses; Indeed emails show only username)
- **Description**: Event description (may be truncated for long descriptions)
- **Attachments**: Names of files attached to the event

## Usage

### Prepare Your Audio
- Place audio files in a single folder (non-recursive scanning)
- **Supported formats**: `.wav`, `.mp3`, `.m4a`, `.aac`
- **Recommendation**: Use WAV format for best reliability
- **Duration display**: Available for all formats (WAV always, AAC/MP3/M4A require mutagen package, fallback to ffprobe if available)
- **Note**: Files are uploaded with the appropriate MIME type based on their format

### Run Meetscribe
```bash
# Using executable
meetscribe process dir <path_to_audio_folder>

# Using source
python -m app.cli process dir <path_to_audio_folder>
```

#### Interactive Single-File Selection
For directories with many files, use interactive selection to choose a specific file:

```bash
# Interactive selection mode
meetscribe process dir <path_to_audio_folder> --select
python -m app.cli process dir <path_to_audio_folder> --select
```

**Controls:**
- **↑/↓ arrows**: Navigate through files within current page
- **←/→ arrows**: Navigate between pages (wraps around)
- **Space**: Toggle selection of the highlighted file (supports multiple selections across pages)
- **Enter**: Confirm selection (processes all selected files, or highlighted file if none selected)
- **Esc or 'q'**: Cancel selection

**Benefits:**
- Preview file metadata (name, size, modification date, duration) before selecting
- Select and process multiple files at once across multiple pages
- Process only the files you need, avoiding unwanted processing
- Clear visual feedback showing selected files and count
- Pagination for large directories with configurable page size
- Files automatically sorted by last modified time (newest first)
- Lazy duration computation for better performance on large directories

#### Additional Commands

```bash
# List audio files with metadata (filename, size, duration, etc.)
meetscribe process list <path_to_audio_folder>

# Process a single file directly
meetscribe process file <path_to_audio_file>
meetscribe process file <path_to_audio_file> --reprocess
```

**Examples**:
```bash
# macOS/Linux
meetscribe process dir "/Users/you/Meetings/2024-09-15"

# Windows
meetscribe process dir "C:\Users\you\Meetings"
```

**Default Behavior**: Meetscribe skips processing audio files when the corresponding output `.txt` file already exists. This saves time and API costs.

**Force Reprocessing**: To reprocess and overwrite existing outputs, use the `--reprocess` flag:
```bash
# Force reprocessing of all files
meetscribe process dir <path_to_audio_folder> --reprocess
```

**Exit Codes**:
- `0`: Success (even if no audio files found)
- `1`: Error (invalid directory path)

**What happens during processing**:
1. Scans the specified folder for supported audio files (non-recursive)
2. Uploads each file to Deepgram for transcription and analysis
3. Saves structured notes as `.txt` files in your output folder
4. Uses the same base filename as the audio file

## Output and Results

### Output Format
For each audio file (e.g., `meeting1.wav`), Meetscribe generates `meeting1.txt` with the following structure:

```markdown
# Meeting Notes

## Summary
[AI-generated summary of the meeting, or "No summary available."]

## Key Decisions
- [Topic 1]
- [Topic 2]
- None  # If no topics detected

## Action Items
- [Action item 1]
- [Action item 2]
- None  # If no action items detected

## Speaker Timeline
- Speaker 0: [Speaker 0's transcript segments]
- Speaker 1: [Speaker 1's transcript segments]
- None  # If diarization data unavailable

---

## Full Transcript
[Complete word-for-word transcription, or "No transcript available."]
```

**Notes:**
- **Summary**: AI-generated overview from Deepgram's summarization
- **Key Decisions**: Topics detected by Deepgram's topic detection
- **Action Items**: Intents detected by Deepgram's intent analysis
- **Speaker Timeline**: Speaker-labeled conversation segments (when diarization is enabled and available)
- **Transcript**: Full speech-to-text conversion with smart formatting

### Deepgram Integration

Meetscribe uses [Deepgram](https://deepgram.com) for AI-powered audio processing:

**Features Used:**
- **Model**: `nova-3` (latest speech recognition model, configurable)
- **Smart Formatting**: Improved punctuation and capitalization
- **Diarization**: Speaker identification and labeling (enabled by default)
- **Summarization**: `v2` AI-generated meeting summaries
- **Topic Detection**: Automatic identification of key topics
- **Intent Analysis**: Detection of action items and tasks

**Technical Details:**
- Files are uploaded entirely to Deepgram's servers
- **Memory Usage**: Audio files are loaded completely into RAM before transmission
- Supports WAV, MP3, M4A, and AAC formats
- MIME types are auto-detected based on file extensions
- **Recommendation**: Use reasonably-sized audio files to avoid memory issues

**Considerations:**
- **Cost**: Billed per minute of audio processed
- **Latency**: Processing time depends on audio length
- **Privacy**: Audio files are sent to Deepgram's secure servers
- **Limits**: Subject to Deepgram's API rate limits and quotas

### Log Files
- **Location**:
  - macOS/Linux: `~/.meetscribe/meetscribe.log`
  - Windows: `C:\Users\<username>\.meetscribe\meetscribe.log`
- **Created**: Automatically on first CLI run
- Check this file for detailed information if issues occur

## Troubleshooting

### Common Issues

**Missing or Empty API Key**
- **Error**: "Deepgram API key not found in config.toml"
- **Solution**: Add your API key to `config.toml` or `config.local.toml`

**No Supported Audio Files Found**
- **Solution**: Ensure your folder contains `.wav`, `.mp3`, `.m4a`, or `.aac` files
- **Tip**: Use `.wav` format for best results

**macOS Cannot Open the App**
- **Solution**: Right-click executable → Open → Open again to bypass security warning

**Slow or Failing Transcriptions**
- **Cause**: Large files or network issues
- **Solution**: Test with a shorter WAV clip first

**Output Not Where Expected**
- **Solution**: Verify the output folder path in `config.toml` under `[paths]`
- **Note**: The app creates the output folder if it doesn't exist

## Privacy and Security
- **Data Processing**: Audio files are uploaded to Deepgram for transcription and analysis
- **Privacy Notice**: Do not use with sensitive recordings unless comfortable with Deepgram's policies
- **API Key Storage**: Keys are stored in plain text locally - keep config files secure

## Tips for Best Results
- Use clear, single-speaker or well-microphoned recordings
- Prefer WAV format for maximum compatibility
- Test with a short sample first to verify setup and output quality
- Keep the app and dependencies updated when running from source
- Use descriptive filenames for better organization

## Getting Help

**CLI Help**:
```bash
meetscribe --help
# or
python -m app.cli --help
```

**Check Logs**:
```bash
# macOS/Linux
tail -f ~/.meetscribe/meetscribe.log

# Windows (PowerShell)
Get-Content ~/.meetscribe/meetscribe.log -Tail 10 -Wait
```

**Report Issues**:
- Open an issue on the project's GitHub repository
- Include: steps to reproduce, log excerpts, and environment details (OS, Python version/build type, error samples)