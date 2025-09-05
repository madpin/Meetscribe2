"""
Action registry for discovering and loading action functions.

This module provides functionality to dynamically discover and load
action functions from the actions directory.
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, Callable, Optional
import logging


def load_action_registry(
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Callable]:
    """
    Scans the 'app/actions' directory to discover and load all available actions.

    Actions are expected to be Python files in the `app/actions` directory.
    The registry maps action names in the format 'module_name.function_name'
    to the actual callable function.

    For example, a function `full()` in `app/actions/screenshot.py` will be
    registered as 'screenshot.full'.

    Args:
        logger: Optional logger for status messages

    Returns:
        dict: A dictionary mapping action names to action functions.
    """
    actions_dir = Path(__file__).parent
    action_registry: Dict[str, Callable] = {}

    if logger:
        logger.info("Loading actions...")
    else:
        print("INFO: Loading actions...")

    for f in actions_dir.glob("*.py"):
        if f.name.startswith("__"):
            continue

        module_name = f.stem
        module_path = f"app.actions.{module_name}"

        try:
            module = importlib.import_module(module_path)
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith("_"):
                    action_name = f"{module_name}.{name}"
                    action_registry[action_name] = func
                    if logger:
                        logger.info(f"Discovered action: {action_name}")
                    else:
                        print(f"INFO: Discovered action: {action_name}")
        except ImportError as e:
            warning_msg = f"Could not import action module {module_path}. Error: {e}"
            if logger:
                logger.warning(warning_msg)
            else:
                print(f"WARNING: {warning_msg}")

    return action_registry
