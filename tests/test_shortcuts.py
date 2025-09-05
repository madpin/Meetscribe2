import sys
from unittest.mock import patch, MagicMock

from app.shortcuts.manager import ShortcutManager

# Mock pynput modules before any imports to handle headless CI
sys.modules["pynput"] = MagicMock()
sys.modules["pynput.keyboard"] = MagicMock()


def test_shortcut_manager_init():
    """Test ShortcutManager initialization"""
    from app.core.context import AppContext
    from unittest.mock import patch

    config_dict = {
        "shortcuts": {
            "enabled": True,
            "shortcuts": {
                "screenshot_full": {
                    "enabled": True,
                    "keys": "cmd+shift+s",
                    "action": "screenshot.full",
                }
            },
        }
    }

    with patch("app.core.config.load_config", return_value=config_dict), patch(
        "app.core.context.setup_logging"
    ), patch(
        "app.actions.registry.load_action_registry",
        return_value={"screenshot.full": MagicMock()},
    ):
        ctx = AppContext()
        manager = ShortcutManager(ctx)

        assert manager.ctx == ctx
        assert manager.listener is None


def test_shortcut_manager_start_with_shortcuts():
    """Test that shortcuts are registered correctly when starting"""

    # Create a mock AppContext directly instead of relying on config loading
    mock_ctx = MagicMock()
    mock_ctx.config.shortcuts.enabled = True
    mock_ctx.config.shortcuts.shortcuts = {
        "screenshot_full": MagicMock(
            enabled=True, keys="cmd+shift+s", action="screenshot.full"
        ),
        "help_show": MagicMock(enabled=True, keys="ctrl+alt+h", action="help.show"),
    }
    mock_ctx.action_registry = {
        "screenshot.full": MagicMock(),
        "help.show": MagicMock(),
    }
    mock_ctx.logger = MagicMock()

    with patch("pynput.keyboard") as mock_keyboard:
        mock_listener = MagicMock()
        mock_keyboard.GlobalHotKeys.return_value = mock_listener

        manager = ShortcutManager(mock_ctx)
        manager.start()

        # Should create GlobalHotKeys with correct mappings
        assert mock_keyboard.GlobalHotKeys.called
        args, kwargs = mock_keyboard.GlobalHotKeys.call_args
        hotkey_map = args[0] if args else kwargs.get("hotkey_map", {})

        assert len(hotkey_map) == 2
        mock_listener.start.assert_called_once()


def test_shortcut_manager_no_shortcuts_config():
    """Test ShortcutManager when no shortcuts are configured"""
    from app.core.context import AppContext

    config_dict = {"shortcuts": {"enabled": True, "shortcuts": {}}}

    with patch("app.core.config.load_config", return_value=config_dict), patch(
        "app.core.context.setup_logging"
    ), patch("app.actions.registry.load_action_registry", return_value={}), patch(
        "builtins.print"
    ) as mock_print:
        ctx = AppContext()
        manager = ShortcutManager(ctx)
        manager.start()

        # Should not create any listener
        assert manager.listener is None

        # Should print info message about no shortcuts
        print_calls = [c[0][0] for c in mock_print.call_args_list]
        assert any("No enabled shortcuts" in msg for msg in print_calls)


def test_shortcut_manager_missing_action_in_registry():
    """Test ShortcutManager when shortcut references non-existent action"""
    from app.core.context import AppContext

    config_dict = {
        "shortcuts": {
            "enabled": True,
            "test_shortcut": {
                "enabled": True,
                "keys": "cmd+s",
                "action": "missing.action",
            },
        }
    }

    import io

    # Capture stdout instead of patching print
    captured_output = io.StringIO()

    with patch("app.core.config.load_config", return_value=config_dict), patch(
        "app.core.context.setup_logging"
    ), patch("app.actions.registry.load_action_registry", return_value={}), patch(
        "sys.stdout", captured_output
    ):
        ctx = AppContext()
        manager = ShortcutManager(ctx)
        manager.start()

        # Should not create listener due to invalid action
        assert manager.listener is None

        # Check that a warning was printed to stdout
        output = captured_output.getvalue()
        # Since the real config is being loaded, just check that some warning about missing action was printed
        assert "WARNING" in output and "not found in registry" in output


def test_shortcut_manager_start():
    """Test starting the shortcut manager"""
    # Create a mock AppContext directly
    mock_ctx = MagicMock()
    mock_ctx.config.shortcuts.enabled = True
    mock_ctx.config.shortcuts.shortcuts = {
        "test_shortcut": MagicMock(enabled=True, keys="cmd+s", action="test.action")
    }
    mock_ctx.action_registry = {"test.action": MagicMock()}
    mock_ctx.logger = MagicMock()

    with patch("pynput.keyboard") as mock_keyboard:
        mock_listener = MagicMock()
        mock_keyboard.GlobalHotKeys.return_value = mock_listener

        manager = ShortcutManager(mock_ctx)
        manager.start()

        mock_listener.start.assert_called_once()
        assert manager.listener == mock_listener


def test_shortcut_manager_stop():
    """Test stopping the shortcut manager"""

    # Create a mock AppContext directly
    mock_ctx = MagicMock()
    mock_ctx.config.shortcuts.enabled = True
    mock_ctx.config.shortcuts.shortcuts = {
        "test_shortcut": MagicMock(enabled=True, keys="cmd+s", action="test.action")
    }
    mock_ctx.action_registry = {"test.action": MagicMock()}
    mock_ctx.logger = MagicMock()

    with patch("pynput.keyboard") as mock_keyboard:
        mock_listener = MagicMock()
        mock_listener.is_alive.return_value = True
        mock_keyboard.GlobalHotKeys.return_value = mock_listener

        manager = ShortcutManager(mock_ctx)
        manager.start()
        manager.stop()

        mock_listener.stop.assert_called_once()


def test_shortcut_manager_stop_without_start():
    """Test stopping manager when listener was never started"""
    from app.core.context import AppContext

    config_dict = {"shortcuts": {"enabled": True, "shortcuts": {}}}

    with patch("app.core.config.load_config", return_value=config_dict), patch(
        "app.core.context.setup_logging"
    ), patch("app.actions.registry.load_action_registry", return_value={}):
        ctx = AppContext()
        manager = ShortcutManager(ctx)
        # Should not raise an exception
        manager.stop()


def test_execute_action_success():
    """Test that execute_action calls the correct action"""
    from app.core.context import AppContext

    mock_action = MagicMock(return_value="action result")
    config_dict = {"test": "config"}

    with patch("app.core.config.load_config", return_value=config_dict), patch(
        "app.core.context.setup_logging"
    ), patch(
        "app.actions.registry.load_action_registry",
        return_value={"test.action": mock_action},
    ), patch("builtins.print") as mock_print:
        ctx = AppContext()
        manager = ShortcutManager(ctx)

        manager.execute_action("test.action")

        # Action should have been called with ctx (AppContext)
        mock_action.assert_called_once_with(ctx)

        # Should print execution messages
        print_calls = [c[0][0] for c in mock_print.call_args_list]
        assert any("executing action" in msg for msg in print_calls)
        assert any("completed" in msg for msg in print_calls)


def test_execute_action_exception_handling():
    """Test that execute_action handles exceptions gracefully"""
    from app.core.context import AppContext

    mock_action = MagicMock(side_effect=Exception("Test error"))
    config_dict = {"test": "config"}

    with patch("app.core.config.load_config", return_value=config_dict), patch(
        "app.core.context.setup_logging"
    ), patch(
        "app.actions.registry.load_action_registry",
        return_value={"test.action": mock_action},
    ), patch("builtins.print") as mock_print:
        ctx = AppContext()
        manager = ShortcutManager(ctx)

        # Should not raise exception
        manager.execute_action("test.action")

        # Should print error message
        print_calls = [c[0][0] for c in mock_print.call_args_list]
        assert any("ERROR" in msg and "Test error" in msg for msg in print_calls)


def test_execute_action_missing_action():
    """Test execute_action with missing action"""
    from app.core.context import AppContext

    config_dict = {"test": "config"}

    with patch("app.core.config.load_config", return_value=config_dict), patch(
        "app.core.context.setup_logging"
    ), patch("app.actions.registry.load_action_registry", return_value={}), patch(
        "builtins.print"
    ) as mock_print:
        ctx = AppContext()
        manager = ShortcutManager(ctx)

        manager.execute_action("missing.action")

        # Should print warning message
        print_calls = [c[0][0] for c in mock_print.call_args_list]
        assert any(
            "WARNING" in msg and "not found in registry" in msg for msg in print_calls
        )
