# armature-plugin-example

Template for building a custom [Armature](https://github.com/vivekgana/armature) plugin.

## What is an Armature plugin?

Plugins extend Armature's quality pipeline with custom checks, healers, or reporters.
They are discovered automatically via Python's `importlib.metadata` entry-points, so
users install them with a simple `pip install` — no config changes required.

## Getting started

1. Copy this directory and rename it:
   ```bash
   cp -r examples/armature-plugin-example my-armature-plugin
   cd my-armature-plugin
   ```

2. Edit `armature_example_plugin.py`:
   - Set `name`, `version`, `description`
   - Implement `on_check`, `on_heal`, and/or `on_gc`

3. Update `pyproject.toml`:
   - Change the package `name`
   - Update the entry-point class reference

4. Install locally and test:
   ```bash
   pip install -e .
   armature plugin list          # should show your plugin
   armature check                # your on_check hook runs automatically
   ```

5. Publish to PyPI:
   ```bash
   pip install build twine
   python -m build
   twine upload dist/*
   ```

## Plugin interface

```python
from armature.plugins import ArmaturePlugin
from armature._internal.types import CheckResult, GCFinding, HealResult

class MyPlugin(ArmaturePlugin):
    name = "my-plugin"
    version = "1.0.0"
    description = "My custom Armature plugin"

    def on_check(self, file_path, results):
        # Add custom check results
        return results + [...]

    def on_heal(self, failures, results):
        # Attempt custom fixes
        return results

    def on_gc(self, findings):
        # Report custom GC findings
        return findings
```

## Full documentation

See the [Armature plugin docs](https://github.com/vivekgana/armature#plugin-architecture).
