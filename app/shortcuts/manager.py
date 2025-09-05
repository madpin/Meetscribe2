"""
Shortcut manager for global keyboard shortcuts.

This module provides functionality to register and manage global keyboard
shortcuts that trigger application actions.
"""

import functools
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.context import AppContext


class ShortcutManager:
    """Manages the global keyboard shortcuts for the application."""

    def __init__(self, ctx: "AppContext"):
        """
        Initializes the ShortcutManager.

        Args:
            ctx: The application context containing configuration and logging.
        """
        self.ctx = ctx
        self.listener = None
        self.ctx.logger.info("ShortcutManager initialized.")

    def execute_action(self, action_name: str) -> None:
        """
        A wrapper to execute a registered action by name.
        This function is used as the callback for all hotkeys.

        Args:
            action_name: Name of the action to execute
        """
        self.ctx.logger.info(f"Shortcut triggered, executing action: '{action_name}'")

        print(f"Shortcut triggered, executing action: '{action_name}'")
        try:
            # Use AppContext's execute_action method for consistent error handling
            result = self.ctx.execute_action(action_name)
            self.ctx.logger.info(f"Action '{action_name}' completed. Result: {result}")
            print(f"Action '{action_name}' completed successfully.")
        except ValueError as e:
            # Action not found - already logged by AppContext
            warning_msg = f"WARNING: Action '{action_name}' not found in registry: {e}"
            print(warning_msg)
        except Exception as e:
            # Other errors - already logged by AppContext
            error_msg = f"ERROR: Action '{action_name}' failed: {e}"
            print(error_msg)

    def start(self) -> None:
        """
        Parses shortcuts from the configuration and starts the listener thread.
        """
        if not self.ctx.config.shortcuts.enabled:
            self.ctx.logger.info("Global shortcuts are disabled in the configuration.")
            return

        shortcuts_map = {}

        # Iterate over the shortcut definitions
        for (
            shortcut_name,
            shortcut_details,
        ) in self.ctx.config.shortcuts.shortcuts.items():
            if shortcut_details.enabled:
                keys = shortcut_details.keys
                action = shortcut_details.action

                if not keys or not action:
                    continue

                if action not in self.ctx.action_registry:
                    warning_msg = f"WARNING: Action '{action}' for shortcut '{keys}' not found in registry. Skipping."
                    self.ctx.logger.warning(warning_msg)
                    print(warning_msg)
                    continue

                # functools.partial creates a new function with the action_name argument "pre-filled".
                # This is how we pass the specific action to the generic execute_action callback.
                callback = functools.partial(self.execute_action, action)
                shortcuts_map[keys] = callback
                self.ctx.logger.info(f"Registering shortcut: {keys} -> {action}")

        if not shortcuts_map:
            self.ctx.logger.info(
                "No enabled shortcuts with valid actions were found to register."
            )
            print("No enabled shortcuts with valid actions were found to register.")
            return

        # Lazy import of pynput.keyboard to avoid display server requirements during import
        try:
            from pynput import keyboard

            # pynput.keyboard.GlobalHotKeys handles listening in a separate thread.
            self.listener = keyboard.GlobalHotKeys(shortcuts_map)
            self.listener.start()
            self.ctx.logger.info(
                "Shortcut listener started and running in a background thread."
            )
        except ImportError as e:
            self.ctx.logger.warning(f"Could not initialize keyboard shortcuts: {e}")
            self.ctx.logger.warning(
                "Keyboard shortcuts will not be available in this environment."
            )
            self.listener = None

    def stop(self) -> None:
        """Stops the keyboard listener thread."""
        if self.listener and self.listener.is_alive():
            self.listener.stop()
            self.ctx.logger.info("Shortcut listener stopped.")
