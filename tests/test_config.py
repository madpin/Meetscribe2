import pytest
import tempfile
import os
from pathlib import Path
from app.core.config import load_config, deep_merge


def test_deep_merge():
    """Test the deep_merge utility function"""
    base = {"a": 1, "b": {"x": 10, "y": 20}, "c": [1, 2, 3]}

    override = {"b": {"y": 30, "z": 40}, "d": "new"}

    result = deep_merge(base, override)

    assert result["a"] == 1
    assert result["b"]["x"] == 10  # preserved from base
    assert result["b"]["y"] == 30  # overridden
    assert result["b"]["z"] == 40  # new from override
    assert result["c"] == [1, 2, 3]  # preserved
    assert result["d"] == "new"  # new from override


def test_load_config_default_only():
    """Test loading config when only default config exists"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a default config
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text("""
[viewer]
log_level = "info"

[paths]
screenshots_folder = "~/screenshots"
        """)

        # Change to temp directory temporarily
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            config = load_config()

            assert config["viewer"]["log_level"] == "info"
            assert config["paths"]["screenshots_folder"] == "~/screenshots"
        finally:
            os.chdir(original_cwd)


def test_load_config_with_local_override():
    """Test loading config with local overrides"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create default config
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text("""
[viewer]
log_level = "info"
theme = "dark"

[paths]
screenshots_folder = "~/screenshots"
        """)

        # Create local override
        local_config_path = Path(tmpdir) / "config.local.toml"
        local_config_path.write_text("""
[viewer]
log_level = "debug"

[paths]
logs_folder = "~/custom_logs"
        """)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            config = load_config()

            # Should have overridden values
            assert config["viewer"]["log_level"] == "debug"
            # Should preserve non-overridden values
            assert config["viewer"]["theme"] == "dark"
            assert config["paths"]["screenshots_folder"] == "~/screenshots"
            # Should have new values from local
            assert config["paths"]["logs_folder"] == "~/custom_logs"
        finally:
            os.chdir(original_cwd)


def test_load_config_missing_default():
    """Test that missing default config raises FileNotFoundError"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            with pytest.raises(
                FileNotFoundError, match="Default configuration file not found"
            ):
                load_config()
        finally:
            os.chdir(original_cwd)


def test_deep_merge_nested_dicts():
    """Test deep merging with deeply nested dictionaries"""
    base = {"level1": {"level2": {"level3": {"value": "original", "keep": "this"}}}}

    override = {
        "level1": {"level2": {"level3": {"value": "overridden"}, "new_level3": "added"}}
    }

    result = deep_merge(base, override)

    assert result["level1"]["level2"]["level3"]["value"] == "overridden"
    assert result["level1"]["level2"]["level3"]["keep"] == "this"
    assert result["level1"]["level2"]["new_level3"] == "added"


def test_deep_merge_empty_cases():
    """Test deep merge with empty dictionaries"""
    assert deep_merge({}, {"a": 1}) == {"a": 1}
    assert deep_merge({"a": 1}, {}) == {"a": 1}
    assert deep_merge({}, {}) == {}


def test_deep_merge_non_dict_override():
    """Test that non-dict values completely override base values"""
    base = {"complex": {"nested": {"data": "value"}}, "simple": "original"}

    override = {"complex": "replaced_entirely", "simple": "new"}

    result = deep_merge(base, override)

    assert result["complex"] == "replaced_entirely"
    assert result["simple"] == "new"
