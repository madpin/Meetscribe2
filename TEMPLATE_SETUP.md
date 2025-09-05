# Template Setup Guide

This guide helps you customize the AIO Terminal Template for your own project. Follow these steps to transform the template into your application.

## 🚀 Quick Setup Checklist

### ⚡ Automated Setup (Recommended)
This template now includes **automatic placeholder replacement**! When you create a repository from this template:

1. **Automatic Replacement**: Placeholders are automatically replaced with your repository information
2. **Validation Issue**: A GitHub issue is created confirming successful setup
3. **Ready to Use**: Your project is immediately configured and ready for development

#### 🔑 Required: Personal Access Token Setup

For the automated setup to work properly (especially to update workflow files), you need to create a Personal Access Token:

1. **Create PAT**: Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. **Generate new token** with these scopes:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
3. **Add as repository secret**:
   - Go to your new repository > Settings > Secrets and variables > Actions
   - Create a new secret named `WORKFLOW_PAT`
   - Paste your token as the value

**Without this PAT**, the automated setup will fail when trying to update workflow files with a permission error.

### Manual Setup (If Automated Setup Fails)

#### 1. Project Identity
- [ ] Update `pyproject.toml` with your project details
- [ ] Rename executable and update references
- [ ] Update documentation and README

#### 2. Configuration
- [ ] Customize `config.toml` defaults
- [ ] Update placeholder URLs and paths
- [ ] Configure your specific shortcuts

#### 3. GitHub Setup
- [ ] Update repository references
- [ ] Configure CI/CD workflows
- [ ] Set up issue templates

#### 4. Code Customization
- [ ] Add your custom actions
- [ ] Update CLI commands and help text
- [ ] Customize logging and error messages

---

## 🔄 Automated Placeholder Replacement

### How It Works

This template includes a GitHub Actions workflow that automatically:

1. **Detects Template Usage**: Runs only when a repository is first created from this template
2. **Extracts Repository Info**: Gets your repository name, owner, and description from GitHub
3. **Replaces Placeholders**: Updates all configuration files with your specific information
4. **Creates Validation Issue**: Opens a GitHub issue confirming successful setup

### Supported Placeholders

| Placeholder | Replaced With | Example |
|-------------|---------------|---------|
| `{{PROJECT_NAME}}` | Repository name | `my-awesome-app` |
| `{{OWNER_NAME}}` | Repository owner | `johndoe` |
| `{{REPO_NAME}}` | Repository name | `my-awesome-app` |
| `{{PROJECT_DESCRIPTION}}` | Repository description | `A cool terminal app` |
| `{{AUTHOR_NAME}}` | Owner's display name | `John Doe` |
| `{{AUTHOR_EMAIL}}` | Owner's email | `john@example.com` |

### What Gets Updated

- ✅ `pyproject.toml` - Project name, description, author info
- ✅ `config.toml` - Log paths, GitHub repository references
- ✅ `README.md` - CI badges, build commands
- ✅ `.github/workflows/ci.yml` - Build commands, artifact names

### Manual Validation

After setup, you can validate everything worked correctly:

```bash
# Run the validation script
python scripts/validate_setup.py

# Or check manually
python -m app.cli --help
```

---

## 📝 Step-by-Step Setup

### Step 1: Update Project Metadata

Edit `pyproject.toml`:

```toml
[project]
name = "your-app-name"                    # Change this
version = "0.1.0"
description = "Your app description"      # Change this

authors = [
    { name = "Your Name", email = "your.email@domain.com" },  # Change this
]

[project.scripts]
your-app-name = "app.cli:app"             # Change entry point name
```

### Step 2: Update Application Identity

**CLI Identity (`app/cli.py`):**
```python
app = typer.Typer(
    name="your-app-name",                  # Change this
    help="Your app description",           # Change this
    no_args_is_help=True,
)
```

**Configuration Paths (`config.toml`):**
```toml
[paths]
logs_folder = "~/.cache/your-app-name/logs"  # Change this

[daemon]
log_file = "/tmp/your-app-name-daemon.log"   # Change this
pid_file = "/tmp/your-app-name-daemon.pid"   # Change this
```

### Step 3: GitHub Repository Setup

**Update README badges:**
```markdown
[![CI](https://github.com/your-username/aio-terminal-template/workflows/CI/badge.svg)](https://github.com/your-username/aio-terminal-template/actions)
```

**Update CI workflow (`.github/workflows/ci.yml`):**
```yaml
# Update artifact names and executable references
name: your-app-name-${{ matrix.os }}
build_cmd: pyinstaller --onefile --name your-app-name app/cli.py
test_cmd: ./dist/your-app-name --help
```

### Step 4: Customize Configuration

**Update API endpoints (`config.toml`):**
```toml
[network]
api_base_url = "https://your-api-domain.com"  # Change this

[updates]
github_repo = "your-username/your-repo"       # Change this
```

**Customize shortcuts (`config.toml`):**
```toml
[shortcuts.your_action]
keys = "<ctrl>+<shift>+y"                     # Choose your shortcuts
action = "your_module.your_function"          # Reference your actions
enabled = true
```

### Step 5: Update Documentation

**README.md:**
- Update project title and description
- Replace example commands with your app name
- Update build instructions
- Add your specific features and usage examples

**Contributing guidelines:**
- Update repository URLs
- Add your project's contribution guidelines
- Update contact information

### Step 6: Customize Actions

**Remove template actions you don't need:**
```bash
# Keep what you need, remove the rest
rm app/actions/screenshot.py    # If not needed
rm app/actions/network.py       # If not needed
rm app/actions/clipboard.py     # If not needed
```

**Add your custom actions:**
```python
# app/actions/your_action.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.context import AppContext

def your_function(ctx: 'AppContext') -> str:
    """Your custom action implementation."""
    ctx.logger.info("Your action executed")
    # Your code here
    return "Success message"
```

## 🔧 Common Customizations

### Adding New Shortcuts

1. Create your action in `app/actions/`
2. Add configuration in `config.toml`:
```toml
[shortcuts.your_shortcut]
keys = "<ctrl>+<shift>+y"
action = "your_module.your_function"
enabled = true
```

### Changing Default Paths

Update `config.toml`:
```toml
[paths]
screenshots_folder = "~/your-preferred-folder"
logs_folder = "~/.cache/your-app/logs"
```

### Customizing Logging

Update `config.toml`:
```toml
[viewer]
log_level = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 🧪 Testing Your Setup

After customization, test these commands:

```bash
# Test the CLI
python -m app.cli --help

# Test configuration
python -m app.cli config show

# Test your actions
python -m app.cli action your_action_name

# Test building
pyinstaller --onefile --name your-app-name app/cli.py
./dist/your-app-name --help
```

## 📋 Template Cleanup Checklist

- [ ] ✅ Updated `pyproject.toml` project metadata
- [ ] ✅ Changed CLI app name and description
- [ ] ✅ Updated configuration paths and URLs
- [ ] ✅ Fixed GitHub repository references
- [ ] ✅ Updated README and documentation
- [ ] ✅ Customized shortcuts and actions
- [ ] ✅ Removed unnecessary template actions
- [ ] ✅ Tested build process
- [ ] ✅ Verified CI/CD configuration

## 🎯 Next Steps After Setup

1. **Add your core functionality** - Implement the main features of your application
2. **Set up CI/CD** - Push to GitHub and enable workflows
3. **Add tests** - Create comprehensive tests for your actions
4. **Documentation** - Write user documentation and API docs
5. **Distribution** - Set up automated releases and packaging

## 🔍 Troubleshooting

**Build fails?**
- Check that all dependencies are in `pyproject.toml`
- Ensure PyInstaller configuration is correct
- Test with `python -m app.cli --help` first

**Actions not found?**
- Verify action files are in `app/actions/`
- Check function names match configuration
- Ensure proper imports in action files

**Shortcuts not working?**
- Check key combinations aren't conflicting
- Verify action references are correct
- Test with `python -m app.cli action <name>`

---

Remember to delete this `TEMPLATE_SETUP.md` file after completing the setup!
