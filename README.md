<p align="center">
  <img src="assets/logo.png" alt="Kypseli Logo" width="200"/>
</p>

<h1 align="center">Kypseli</h1>

<p align="center">
  <strong>The AI-Powered File Organization Hive</strong>
</p>

<p align="center">
  <a href="https://github.com/IoanRoume/kypseli/releases/latest">
    <img src="https://img.shields.io/github/v/release/IoanRoume/kypseli?style=flat-square" alt="Latest Release"/>
  </a>
  <a href="https://github.com/IoanRoume/kypseli/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/IoanRoume/kypseli?style=flat-square" alt="License"/>
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square" alt="Python 3.10+"/>
  </a>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="#ai-providers">AI Providers</a> •
  <a href="#configuration">Configuration</a>
</p>

---

## Overview

Kypseli (Greek for "beehive") is a command-line tool that uses artificial intelligence to automatically organize your files. Instead of manually sorting downloads, documents, and data files into folders, Kypseli analyzes each file's content, name, and metadata to intelligently classify and move it to the appropriate location.

**Key Features:**

- **AI-Powered Classification** — Uses large language models to understand file context and purpose
- **Multiple AI Providers** — Supports OpenAI, Anthropic, Google Gemini, Groq, Mistral, Cohere, Ollama, and more
- **Background Service** — Watches directories and automatically organizes new files as they arrive
- **File Analysis** — Deep inspection of tabular data, code files, and documents with AI-generated insights
- **Configurable Folders** — Define custom folder structures with descriptions to guide the AI
- **Operation History** — Track all file operations with full audit trail
- **Cross-Platform** — Works on Windows, macOS, and Linux

---

## Installation

### Linux and macOS

Run the install script:
```bash
curl -fsSL https://raw.githubusercontent.com/IoanRoume/kypseli/main/install.sh | sh
```

After installation, reload your shell:
```bash
source ~/.bashrc   # or ~/.zshrc for Zsh
```

Verify the installation:
```bash
kypseli version
```

#### Manual Installation (Linux/macOS)

1. Download the latest release for your platform:
   - [kypseli-linux](https://github.com/IoanRoume/kypseli/releases/latest/download/kypseli-linux)
   - [kypseli-macos](https://github.com/IoanRoume/kypseli/releases/latest/download/kypseli-macos)

2. Make it executable and move to your PATH:
```bash
chmod +x kypseli-linux
sudo mv kypseli-linux /usr/local/bin/kypseli
```

3. (Optional) Enable shell completions:
```bash
# For Bash
echo 'eval "$(_KYPSELI_COMPLETE=bash_source kypseli)"' >> ~/.bashrc

# For Zsh
echo 'eval "$(_KYPSELI_COMPLETE=zsh_source kypseli)"' >> ~/.zshrc
```

### Windows

1. Download the installer: [kypseli-windows-installer.exe](https://github.com/IoanRoume/kypseli/releases/latest/download/kypseli-windows-installer.exe)

2. Run the installer. It will:
   - Install Kypseli to `C:\Program Files\Kypseli`
   - Add Kypseli to your system PATH

3. Open a new Command Prompt or PowerShell window and verify:
```powershell
kypseli version
```

### From Source (Python)

Requires Python 3.10 or higher.
```bash
git clone https://github.com/IoanRoume/kypseli.git
cd kypseli
pip install .
```

---

## Quick Start

### 1. Set Up an AI Provider

Kypseli requires an AI provider for file classification. The easiest option is OpenAI:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

See [AI Providers](#ai-providers) for all available options including free and local alternatives.

### 2. Organize Files (Dry Run)

Preview what Kypseli would do without moving any files:
```bash
kypseli organize ~/Downloads --defaults
```

### 3. Execute Organization

Move files to their classified folders:
```bash
kypseli organize ~/Downloads --defaults --mode move --yes
```

### 4. Start Background Service

Automatically organize new files as they appear:
```bash
kypseli service start ~/Downloads --defaults
```

---

## Commands

### organize

Organize files in a directory using AI classification.
```bash
kypseli organize <directory> [options]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--mode` | `-m` | Operation mode: `dry_run` (default), `move`, or `copy` |
| `--provider` | `-p` | AI provider to use (default: `openai`) |
| `--model` | | Specific model to use |
| `--output` | `-o` | Base directory for organized folders (default: `./organized`) |
| `--defaults` | `-d` | Use default folder configuration |
| `--config` | `-c` | Use a saved configuration by name |
| `--save-config` | | Save the folder configuration with a name |
| `--analyze` | `-a` | Run detailed analysis on each file |
| `--yes` | `-y` | Execute without confirmation |
| `--base-url` | | Base URL for OpenAI-compatible providers |

**Examples:**
```bash
# Preview organization with default folders
kypseli organize ./Downloads --defaults

# Move files using GPT-4o
kypseli organize ./Downloads --defaults --mode move --provider openai --model gpt-4o

# Use a saved configuration
kypseli organize ./Downloads --config work_setup --mode move

# Organize and analyze files
kypseli organize ./Downloads --defaults --analyze

# Use Ollama (local)
kypseli organize ./Downloads --defaults --provider ollama --model llama3.1:8b

# Use Groq (fast, free tier available)
kypseli organize ./Downloads --defaults --provider groq
```

**Default Folder Structure:**

When using `--defaults`, files are organized into:

| Folder | Description |
|--------|-------------|
| `Datasets/` | CSV, Excel, Parquet, Pickle, and other tabular data |
| `Documents/` | PDFs, Word documents, and text documents |
| `Code/` | Python, JavaScript, and other programming files |
| `Images/` | PNG, JPG, GIF, and other image formats |
| `Videos/` | MP4, MOV, AVI, and other video formats |
| `Archives/` | ZIP, TAR, RAR, and compressed files |
| `Other/` | Files that don't match any category |

---

### scan

Scan a directory and display file information without organizing.
```bash
kypseli scan <directory>
```

**Example:**
```bash
kypseli scan ~/Downloads
```

Output shows file name, extension, size, type, and modification date with a summary by file type.

---

### service

Manage the background file watcher service that automatically organizes new files.

#### service start

Start watching a directory for new files.
```bash
kypseli service start <directory> [options]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--defaults` | `-d` | Use default folder configuration |
| `--config` | `-c` | Use a saved configuration |
| `--provider` | `-p` | AI provider (default: `openai`) |
| `--model` | | Model to use |
| `--output` | `-o` | Base directory for organized folders |
| `--cooldown` | | Seconds to wait before processing (default: 5) |
| `--process-existing` | `-e` | Process existing files before watching |
| `--save-config` | | Save configuration for reuse |
| `--base-url` | | Base URL for OpenAI-compatible providers |

**Examples:**
```bash
# Start with defaults
kypseli service start ~/Downloads --defaults

# Process existing files then watch for new ones
kypseli service start ~/Downloads --defaults --process-existing

# Use a specific provider and save the configuration
kypseli service start ~/Downloads --defaults --provider groq --save-config downloads_watcher
```

#### service stop

Stop the background service.
```bash
kypseli service stop
```

#### service status

Show the current service status.
```bash
kypseli service status
```

#### service logs

View service logs.
```bash
kypseli service logs [options]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--lines` | `-n` | Number of lines to show (default: 50) |
| `--follow` | `-f` | Follow log output in real-time |

**Examples:**
```bash
# View last 50 lines
kypseli service logs

# Follow logs in real-time
kypseli service logs --follow

# View last 100 lines
kypseli service logs --lines 100
```

#### service restart

Restart the service with the previous configuration.
```bash
kypseli service restart
```

---

### analyze

Analyze files and generate detailed insights.

#### analyze file

Analyze a single file.
```bash
kypseli analyze file <file_path> [options]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--provider` | `-p` | AI provider for descriptions |
| `--model` | | Model to use |
| `--save/--no-save` | | Save analysis to database (default: save) |
| `--base-url` | | Base URL for OpenAI-compatible providers |

**Example:**
```bash
kypseli analyze file ./data.csv --provider openai
```

**Supported Analysis Types:**

| File Type | Analysis Includes |
|-----------|-------------------|
| Tabular (CSV, Excel, Parquet) | Row/column count, data types, missing values, memory usage, AI description |
| Code (Python, JS, etc.) | Language, line count, imports, functions, classes, complexity estimate |
| Documents (PDF, DOCX) | Page count, word count, language, key topics, summary |

#### analyze dir

Analyze all supported files in a directory.
```bash
kypseli analyze dir <directory> [options]
```

#### analyze history

View recent analysis history.
```bash
kypseli analyze history [options]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--limit` | `-n` | Number of records to show (default: 20) |
| `--verbose` | `-v` | Show full analysis details |

---

### config

Manage saved folder configurations.

#### config list

List all saved configurations.
```bash
kypseli config list
```

#### config show

Show details of a saved configuration.
```bash
kypseli config show <name>
```

#### config delete

Delete a saved configuration.
```bash
kypseli config delete <name>
```

---

### history

View file operation history.

#### history list

Show recent operations.
```bash
kypseli history list [options]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--limit` | `-n` | Number of records (default: 20) |
| `--verbose` | `-v` | Show full details and reasoning |

#### history search

Search for a file in history.
```bash
kypseli history search <filename>
```

#### history stats

Show operation statistics.
```bash
kypseli history stats
```

---

### providers

List available AI providers and their status.
```bash
kypseli providers
```

Shows each provider, whether the required package is installed, API key status, and default model.

---

### version

Display version information.
```bash
kypseli version
```

---

## AI Providers

Kypseli supports multiple AI providers. Configure your preferred provider using environment variables.

### Cloud Providers

| Provider | Environment Variable | Default Model | Free Tier |
|----------|---------------------|---------------|-----------|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` | No |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | No |
| Google Gemini | `GOOGLE_API_KEY` | `gemini-2.0-flash` | Yes |
| Groq | `GROQ_API_KEY` | `llama-3.1-8b-instant` | Yes |
| Mistral | `MISTRAL_API_KEY` | `mistral-small-latest` | Yes |
| Cohere | `COHERE_API_KEY` | `command-r` | Yes |
| DeepInfra | `DEEPINFRA_API_TOKEN` | `google/gemma-3-27b-it` | Yes |

### Local Providers

#### Ollama

Run models locally on your machine.

1. Install Ollama: https://ollama.com
2. Pull a model: `ollama pull llama3.1:8b`
3. Start Ollama: `ollama serve`
4. Use with Kypseli:
```bash
kypseli organize ./Downloads --defaults --provider ollama --model llama3.1:8b
```

#### OpenAI-Compatible

Use any OpenAI-compatible API (LM Studio, vLLM, LocalAI).
```bash
kypseli organize ./Downloads --defaults \
  --provider openai-compatible \
  --model local-model \
  --base-url http://localhost:1234/v1
```

### Setting Environment Variables

**Linux/macOS:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."
```

**Windows (PowerShell):**
```powershell
# Temporary (current session)
$env:OPENAI_API_KEY = "sk-..."

# Permanent
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-...", "User")
```

**Windows (Command Prompt):**
```cmd
setx OPENAI_API_KEY "sk-..."
```

---

## Configuration

### Data Storage

Kypseli stores its data in `~/.file_organizer/`:
```
~/.file_organizer/
├── file_organizer.db    # SQLite database (configs, history, analyses)
└── service/
    ├── watcher.pid      # Service process ID
    ├── watcher.log      # Service logs
    └── watcher_config.json  # Active service configuration
```

### Custom Folder Configuration

Instead of using `--defaults`, you can define custom folders interactively:
```bash
kypseli organize ./Downloads
```

Follow the prompts to create folders with descriptions. The AI uses these descriptions to classify files.

Save your configuration for reuse:
```bash
kypseli organize ./Downloads --save-config my_setup
```

Use it later:
```bash
kypseli organize ./Downloads --config my_setup --mode move
```

---

## Supported File Types

Kypseli can process and classify a wide variety of file types:

| Category | Extensions |
|----------|------------|
| Tabular | `.csv`, `.xlsx`, `.xls`, `.parquet`, `.pkl`, `.pickle`, `.json`, `.tsv`, `.feather`, `.h5`, `.hdf5` |
| Documents | `.pdf`, `.docx`, `.doc`, `.txt`, `.rtf`, `.odt`, `.epub` |
| Code | `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`, `.scala`, `.r`, `.sql`, `.sh`, `.bash`, `.lua`, `.pl`, `.html`, `.css`, `.yaml`, `.yml`, `.toml`, `.xml`, `.md` |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.svg`, `.ico`, `.heic`, `.heif`, `.tiff` |
| Videos | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.wmv`, `.m4v` |
| Archives | `.zip`, `.tar`, `.gz`, `.rar`, `.7z`, `.bz2`, `.xz` |

---

## Troubleshooting

### "API key not configured"

Set the appropriate environment variable for your provider. See [AI Providers](#ai-providers).

### "Model not found"

Verify the model name is correct. Use `kypseli providers` to see default models.

### Service won't stop (Windows)

If `kypseli service stop` doesn't work, manually kill the process:
```powershell
# Find the process
Get-Process | Where-Object {$_.ProcessName -like "*kypseli*"}

# Kill it
Stop-Process -Name kypseli -Force
```

### Slow startup (Windows)

This is normal for the first run. Subsequent runs are faster.

### Ollama connection refused

Ensure Ollama is running:
```bash
ollama serve
```

And verify a model is pulled:
```bash
ollama list
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---
