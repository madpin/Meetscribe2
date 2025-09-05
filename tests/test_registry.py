from app.actions.registry import load_action_registry


def test_load_action_registry():
    """
    Tests that the action registry can discover and load actions correctly.
    """
    # The print statements in the function will show up during the test run
    registry = load_action_registry()

    # 1. The registry should discover at least one action
    assert registry
    assert isinstance(registry, dict)

    # 2. It should contain our specific 'screenshot.full' action
    assert "screenshot.full" in registry

    # 3. The discovered action should be a callable function
    action_func = registry["screenshot.full"]
    assert callable(action_func)

    # 4. Check for the other action that might be discovered (the registry itself)
    # This is a side-effect of the current implementation, but good to be aware of.
    assert "registry.load_action_registry" in registry
    assert callable(registry["registry.load_action_registry"])
