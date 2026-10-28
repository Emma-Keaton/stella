# plugins/_template.py — Drop-in plugin template.
#
# Copy this file to a new .py file in plugins/ (without the _ prefix),
# customize the PLUGIN dict and run() function, and Stella will auto-discover
# it on next launch. No restart required to toggle enablement.

PLUGIN = {
    "name":        "my_plugin",
    "description": "Describe what your plugin does for Gemini routing.",
    "parameters":  {
        "type": "OBJECT",
        "properties": {
            "example_arg": {"type": "STRING", "description": "An example parameter"}
        },
        "required": ["example_arg"],
    },
    "behavior":    "BLOCKING",       # BLOCKING | NON_BLOCKING
    "scheduling":  "WHEN_IDLE",      # WHEN_IDLE | SILENT | INTERRUPT
    "tier":        "extra",          # core | extra (for tool budgeting)
    "brief":       "Short description",  # for tight budgets
}

PLUGIN_SETTINGS = {                  # optional settings schema for UI
    "namespace": "my_plugin",
    "title": "My Plugin",
    "fields": [
        {"key": "example_arg", "label": "Example Argument", "type": "string"}
    ],
    "action": "test",                 # optional test/connect button
}

def run(parameters: dict, player=None, session_memory=None) -> str:
    """
    Plugin handler.
    - parameters: dict of args extracted by the model
    - player: StellaUI instance (for write_log, etc.)
    - session_memory: reserved
    Returns a short spoken string. Never raise.
    """
    arg = parameters.get("example_arg", "")
    return f"My plugin received: {arg}"
