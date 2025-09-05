"""
Action: Application update checking and information.

This action checks for newer versions of the application on GitHub
and provides information about the current version and available updates.
It also supports automatic updates for executable-only installations.
"""

import os
import platform
import requests
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..core.context import AppContext


def update_now(ctx: "AppContext") -> str:
    """
    Automatically download and install the latest version of the application.

    This function checks for updates and if available, downloads and installs
    the new executable, replacing the current one safely.

    Args:
        ctx: The application's context containing configuration and logging.

    Returns:
        str: Update installation status.
    """
    ctx.logger.info("Executing action: app.update_now")

    repo = ctx.config.updates.github_repo
    if not repo:
        ctx.logger.warning("No GitHub repository configured for updates")
        return "❌ No GitHub repository configured for updates"

    # Get current version
    current_version = _get_current_version()
    ctx.logger.info(f"Current version: {current_version}")

    # Check for updates
    latest_info = _get_latest_release(repo)
    if not latest_info:
        return "❌ Failed to check for updates"

    latest_version = latest_info["tag_name"]

    if not _is_newer_version(latest_version, current_version):
        return f"✅ Already up to date\nCurrent: {current_version}\nLatest:  {latest_version}"

    # Get download URL for current platform
    # Try to get executable name from config, fallback to auto-detection
    executable_name = getattr(ctx.config.updates, "executable_name", None)
    download_url = _get_download_url(latest_info, executable_name)
    if not download_url:
        return "❌ No compatible download found for your platform"

    ctx.logger.info(f"Downloading update from: {download_url}")

    # Download and install
    try:
        return _download_and_install_update(ctx, download_url, latest_version)
    except Exception as e:
        ctx.logger.error(f"Update installation failed: {e}")
        return f"❌ Update failed: {str(e)}"


def _get_download_url(release_info: dict, project_name: str = None) -> Optional[str]:
    """
    Get the appropriate download URL for the current platform from GitHub release.

    Args:
        release_info: GitHub release information from API
        project_name: Name of the project (defaults to detecting from executable)

    Returns:
        str: Download URL or None if not found
    """
    system = platform.system().lower()
    assets = release_info.get("assets", [])

    # Detect project name from current executable if not provided
    if project_name is None:
        current_exe = _get_current_executable_path()
        if current_exe:
            project_name = os.path.splitext(os.path.basename(current_exe))[0]
        else:
            project_name = "aio_terminal_template"  # fallback

    # Map platform names to expected asset name patterns
    platform_patterns = {
        "linux": [f"{project_name}-linux", "linux"],
        "darwin": [f"{project_name}-macos", "macos"],
        "windows": [f"{project_name}-windows.exe", "windows.exe"],
    }

    patterns = platform_patterns.get(system, [])
    if not patterns:
        return None

    for asset in assets:
        asset_name = asset["name"].lower()
        for pattern in patterns:
            if pattern in asset_name:
                return asset["browser_download_url"]

    return None


def _download_and_install_update(
    ctx: "AppContext", download_url: str, new_version: str
) -> str:
    """
    Download and install the update safely.

    Args:
        ctx: Application context
        download_url: URL to download the new executable
        new_version: Version string of the new release

    Returns:
        str: Installation status message
    """
    # Get current executable path
    current_exe = _get_current_executable_path()
    if not current_exe:
        return "❌ Could not determine current executable path"

    ctx.logger.info(f"Current executable: {current_exe}")

    # Create backup
    backup_path = f"{current_exe}.backup"
    try:
        import shutil

        shutil.copy2(current_exe, backup_path)
        ctx.logger.info(f"Created backup: {backup_path}")
    except Exception as e:
        ctx.logger.warning(f"Failed to create backup: {e}")

    # Download to temporary file
    try:
        ctx.logger.info("Downloading update...")
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()

        # Get total file size for progress indication
        total_size = int(response.headers.get("content-length", 0))

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=_get_executable_suffix()
        ) as temp_file:
            temp_path = temp_file.name

            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    downloaded += len(chunk)

            # Make executable on Unix-like systems
            if platform.system() != "Windows":
                os.chmod(temp_path, 0o755)

        ctx.logger.info(f"Downloaded {downloaded} bytes to {temp_path}")

        # Replace executable
        _replace_executable_safely(current_exe, temp_path, ctx)

        return f"""✅ Update successful!
New version: {new_version}
Backup created: {backup_path}

Please restart the application to use the new version."""

    except Exception as e:
        # Cleanup temporary file
        try:
            if "temp_path" in locals():
                os.unlink(temp_path)
        except (OSError, FileNotFoundError):
            pass

        # Restore backup if something went wrong
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, current_exe)
                ctx.logger.info("Restored from backup")
        except (OSError, IOError) as backup_error:
            ctx.logger.error(f"Failed to restore backup: {backup_error}")

        raise e


def _get_current_executable_path() -> Optional[str]:
    """
    Get the path to the currently running executable.

    Returns:
        str: Path to executable or None if not found
    """
    try:
        # PyInstaller sets sys.executable to the executable path
        if hasattr(sys, "_MEIPASS"):  # Running in PyInstaller bundle
            return sys.executable

        # Fallback for development
        return sys.executable
    except Exception:
        return None


def _get_executable_suffix() -> str:
    """
    Get the appropriate executable suffix for the current platform.

    Returns:
        str: File extension (.exe on Windows, empty otherwise)
    """
    return ".exe" if platform.system() == "Windows" else ""


def _replace_executable_safely(
    current_path: str, new_path: str, ctx: "AppContext"
) -> None:
    """
    Safely replace the current executable with the new one.

    Args:
        current_path: Path to current executable
        new_path: Path to new executable
        ctx: Application context for logging
    """
    import shutil

    # On Windows, we need to be careful about file locking
    if platform.system() == "Windows":
        # Try to replace directly
        try:
            shutil.move(new_path, current_path)
            ctx.logger.info("Executable replaced successfully")
        except Exception as e:
            # If direct replacement fails, try to use a batch file for replacement on next startup
            ctx.logger.warning(f"Direct replacement failed: {e}")
            _schedule_windows_replacement(current_path, new_path, ctx)
    else:
        # On Unix-like systems, replacement is usually straightforward
        try:
            shutil.move(new_path, current_path)
            ctx.logger.info("Executable replaced successfully")
        except Exception as e:
            ctx.logger.error(f"Failed to replace executable: {e}")
            raise e


def _schedule_windows_replacement(
    current_path: str, new_path: str, ctx: "AppContext"
) -> None:
    """
    Schedule executable replacement for Windows using a batch file.

    Args:
        current_path: Path to current executable
        new_path: Path to new executable
        ctx: Application context for logging
    """
    batch_content = f"""@echo off
timeout /t 2 /nobreak > nul
move "{new_path}" "{current_path}"
del "%~f0"
"""

    batch_path = f"{current_path}.update.bat"
    try:
        with open(batch_path, "w") as f:
            f.write(batch_content)
        ctx.logger.info(f"Created update batch file: {batch_path}")

        # Try to run the batch file immediately (might work if current exe is not locked)
        try:
            subprocess.run([batch_path], shell=True, check=False)
        except (subprocess.SubprocessError, OSError):
            pass

    except Exception as e:
        ctx.logger.error(f"Failed to create update batch file: {e}")
        # Fallback to direct replacement
        try:
            import shutil

            shutil.move(new_path, current_path)
        except (OSError, IOError) as fallback_error:
            ctx.logger.error(f"Fallback replacement also failed: {fallback_error}")
            raise fallback_error


def update_check(ctx: "AppContext") -> str:
    """
    Check for application updates on GitHub.

    Args:
        ctx: The application's context containing configuration and logging.

    Returns:
        str: Update status information.
    """
    ctx.logger.info("Executing action: app.update_check")

    repo = ctx.config.updates.github_repo
    if not repo:
        ctx.logger.warning("No GitHub repository configured for updates")
        return "❌ No GitHub repository configured for updates"

    # Get current version (from pyproject.toml or version file)
    current_version = _get_current_version()
    ctx.logger.info(f"Current version: {current_version}")

    # Check GitHub for latest release
    latest_info = _get_latest_release(repo)

    if latest_info:
        latest_version = latest_info["tag_name"]
        published_at = latest_info["published_at"]

        if _is_newer_version(latest_version, current_version):
            result = f"""🎉 Update available!
Current: {current_version}
Latest:  {latest_version}
Published: {published_at}

Release notes: {latest_info['html_url']}
"""
            ctx.logger.info(f"Update available: {latest_version}")
        else:
            result = (
                f"✅ Up to date\nCurrent: {current_version}\nLatest:  {latest_version}"
            )
            ctx.logger.info("Application is up to date")

        return result
    else:
        return "❌ Failed to check for updates"


def _get_current_version() -> str:
    """
    Get the current application version.

    Returns:
        str: Current version string
    """
    try:
        # Try to read from pyproject.toml
        import tomllib

        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")
    except Exception:
        pass

    try:
        # Fallback: try to read from version file

        with open("VERSION", "r") as f:
            return f.read().strip()
    except Exception:
        pass

    return "dev"  # Development version


def _get_latest_release(repo: str) -> Optional[dict]:
    """
    Get the latest release information from GitHub.

    Args:
        repo: GitHub repository in format "owner/repo"

    Returns:
        dict: Latest release information or None if failed
    """
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            return None

    except Exception as e:
        print(f"Failed to fetch release info: {e}")
        return None


def _is_newer_version(latest: str, current: str) -> bool:
    """
    Compare version strings to determine if latest is newer than current.

    Args:
        latest: Latest version string
        current: Current version string

    Returns:
        bool: True if latest is newer
    """
    # Simple version comparison - could be enhanced with proper semver parsing
    try:
        # Remove 'v' prefix if present
        latest = latest.lstrip("v")
        current = current.lstrip("v")

        if latest == current:
            return False

        # For development versions
        if current == "dev":
            return True

        # Split by dots and compare
        latest_parts = latest.split(".")
        current_parts = current.split(".")

        # Pad shorter version with zeros
        max_len = max(len(latest_parts), len(current_parts))
        latest_parts.extend(["0"] * (max_len - len(latest_parts)))
        current_parts.extend(["0"] * (max_len - len(current_parts)))

        for l_part, c_part in zip(latest_parts, current_parts):
            # Handle non-numeric parts
            if l_part.isdigit() and c_part.isdigit():
                l_num, c_num = int(l_part), int(c_part)
                if l_num > c_num:
                    return True
                elif l_num < c_num:
                    return False
            else:
                # String comparison for pre-release tags, etc.
                if l_part > c_part:
                    return True
                elif l_part < c_part:
                    return False

        return False

    except Exception:
        # If version comparison fails, assume update is available
        return True


def version(ctx: "AppContext") -> str:
    """
    Get current application version information.

    Args:
        ctx: The application's context containing configuration and logging.

    Returns:
        str: Version information
    """
    ctx.logger.info("Getting application version")

    version = _get_current_version()
    return f"AIO Terminal Template v{version}"
