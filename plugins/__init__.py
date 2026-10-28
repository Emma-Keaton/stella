# plugins/ — Drop-in user plugins (Mark-LVI PLUGIN dict pattern)
#
# Each plugin is its own .py file with a module-level PLUGIN dict + run() function.
# Files starting with _ are skipped (template/helpers).
# Auto-discovered by plugin_loader.py at startup.
# Enablement stored in api_keys.json (plugins_enabled) — toggle without restart.
