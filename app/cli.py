"""
Terminal application CLI with Typer.

This module provides the command-line interface for the terminal application,
using the new AppContext architecture for dependency management.
"""

import typer
import json
import time
import sys
from typing import Annotated, Optional

from app.core.context import AppContext
from app.core.exceptions import ConfigurationError

# Global AppContext instance - will be initialized on first use
_app_context: Optional[AppContext] = None


def get_app_context() -> AppContext:
    """Get or create the global application context."""
    global _app_context
    if _app_context is None:
        try:
            _app_context = AppContext()
        except ConfigurationError as e:
            print(f"Configuration error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to initialize application: {e}")
            sys.exit(1)
    return _app_context


app = typer.Typer(
    name="aio_terminal_template",
    help="A terminal-first application with global shortcuts and rich logging.",
    no_args_is_help=True,
)

daemon_app = typer.Typer(name="daemon", help="Control the background listener.")
config_app = typer.Typer(name="config", help="Manage settings.")
logs_app = typer.Typer(name="logs", help="View and manage logs.")
update_app = typer.Typer(name="update", help="Check for newer releases.")

app.add_typer(daemon_app)
app.add_typer(config_app)
app.add_typer(logs_app)
app.add_typer(update_app)


@app.command()
def run(
    safe_mode: Annotated[
        bool,
        typer.Option("--safe-mode", help="Start without loading global hotkeys."),
    ] = False,
):
    """Start the live viewer and shortcut listener."""
    ctx = get_app_context()
    print("Starting application in live mode...")
    ctx.logger.info("Starting application in live mode...")

    manager = None
    if safe_mode:
        print("Running in Safe Mode. Shortcuts will not be loaded.")
        ctx.logger.info("Running in Safe Mode. Shortcuts will not be loaded.")
    else:
        # Instantiate and start the shortcut manager with AppContext
        from app.shortcuts.manager import ShortcutManager

        manager = ShortcutManager(ctx)
        manager.start()

    ctx.logger.info("Application running. Press Ctrl+C to exit.")
    try:
        # Keep the main thread alive to allow the listener thread to run.
        # This part will be replaced by the Rich UI event loop later.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutdown signal received. Cleaning up...")
        ctx.logger.info("Shutdown signal received. Cleaning up...")
        if manager:
            manager.stop()
        print("Shutdown complete.")
        ctx.logger.info("Shutdown complete.")


@daemon_app.command()
def start():
    """Start the background listener (daemon)."""
    print("Starting daemon...")
    # Placeholder for daemon start logic
    pass


@daemon_app.command()
def stop():
    """Stop the background listener (daemon)."""
    print("Stopping daemon...")
    # Placeholder for daemon stop logic
    pass


@daemon_app.command()
def status():
    """Check the status of the background listener."""
    print("Checking daemon status...")
    # Placeholder for daemon status logic
    pass


@app.command()
def action(name: Annotated[str, typer.Argument(help="The name of the action to run.")]):
    """Run any action directly from the CLI."""
    ctx = get_app_context()
    ctx.logger.info(f"Attempting to run action: {name}")

    try:
        result = ctx.execute_action(name)
        ctx.logger.info(f"Action '{name}' executed successfully. Result: {result}")
        print(result)  # Print result for CLI feedback
    except ValueError as e:
        # Action not found - error already logged, but also print for CLI
        print(f"Error: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        # Action execution error - error already logged, but also print for CLI
        print(f"Error: {e}")
        raise typer.Exit(code=1)


@config_app.command()
def show():
    """Show the current configuration."""
    ctx = get_app_context()

    # Convert dataclass config back to dict for JSON display
    def dataclass_to_dict(obj):
        if hasattr(obj, "__dataclass_fields__"):
            result = {}
            for field_name, field_info in obj.__dataclass_fields__.items():
                value = getattr(obj, field_name)
                if hasattr(value, "__dataclass_fields__"):
                    result[field_name] = dataclass_to_dict(value)
                elif isinstance(value, dict):
                    result[field_name] = {
                        k: dataclass_to_dict(v)
                        if hasattr(v, "__dataclass_fields__")
                        else v
                        for k, v in value.items()
                    }
                else:
                    result[field_name] = value
            return result
        return obj

    config_dict = dataclass_to_dict(ctx.config)
    print(json.dumps(config_dict, indent=2))


@config_app.command()
def edit():
    """Open the configuration file in the default editor."""
    print("Opening configuration file...")
    # Placeholder for editing config
    pass


@config_app.command()
def reset():
    """Reset the configuration to default settings."""
    print("Resetting configuration...")
    # Placeholder for resetting config
    pass


@logs_app.command()
def tail():
    """Tail the live log file."""
    print("Tailing logs...")
    # Placeholder for log tailing
    pass


@logs_app.command()
def open():
    """Open the log folder in the file explorer."""
    print("Opening log folder...")
    # Placeholder for opening log folder
    pass


@logs_app.command()
def clear():
    """Clear all log files."""
    print("Clearing logs...")
    # Placeholder for clearing logs
    pass


@update_app.command()
def check():
    """Check for a newer release on GitHub."""
    ctx = get_app_context()
    ctx.logger.info("Checking for updates...")

    try:
        result = ctx.execute_action("app.update_check")
        print(result)
    except ValueError as e:
        # Action not found - error already logged
        print(f"❌ Update check failed: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        # Action execution error - error already logged
        print(f"❌ Update check error: {e}")
        raise typer.Exit(code=1)


@update_app.command()
def now():
    """Download and install the latest version automatically."""
    ctx = get_app_context()
    ctx.logger.info("Starting automatic update...")

    try:
        result = ctx.execute_action("app.update_now")
        print(result)
    except ValueError as e:
        # Action not found - error already logged
        print(f"❌ Update failed: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        # Action execution error - error already logged
        print(f"❌ Update error: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
