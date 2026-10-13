# Model Management

The public build of Stella ships with no pre-loaded local model. You download
models yourself, switch between them per task, and delete or replace them when
you like. Everything is managed from **Settings → Local Models**.

## How it works

- Downloaded models are stored as `.gguf` files under the user data directory's
  `models/` folder.
- The currently active model and its endpoint are recorded in the `models`
  section of `config/app_settings.json`.
- When a model is selected, Stella points its local AI client at that model's
  server endpoint and uses it for local reasoning tasks.

## Settings → Local Models

The Local Models panel shows:

- **Downloaded models** — every `.gguf` found in the models folder, with size,
  quantization, and an "active" marker on the selected one.
- **Download** — browse device-appropriate models. Stella detects your CPU,
  RAM, and GPU and only recommends models that fit. Downloads go to the models
  folder.
- **Switch** — make a downloaded model the active one. Stella probes the local
  model server endpoint and wires it into the chat path.
- **Delete** — remove a model from disk (with a confirmation dialog). If it was
  the active model, Stella clears the selection.
- **Replace** — delete the current model and download a different one in a
  single flow.

## Programmatic API

`agent/model_manager.py` exposes the same operations for scripts and tests:

```python
from agent import model_manager as mm

mm.detect_device()                     # CPU / RAM / GPU profile
mm.list_downloaded_models()            # all local .gguf models
mm.get_selected_model()                # active model + endpoint, or None
mm.set_selected_model(model_dict)      # make a model active
mm.download_model({"repo": ..., "file": ...}, progress=cb)
mm.delete_model(model_dict)
mm.replace_model(old_model, new_demo)
```

Settings are read/written through `load_model_settings()` and
`save_model_settings()`, which merge into the `models` key of
`app_settings.json` without disturbing other settings.

## Choosing the right model

Stella's device detection buckets your machine (low-end / mid-end / high-end)
and recommends quantizations that fit your free RAM. As a rule of thumb:

- **~2 GB free RAM** — 1–3B parameter models at Q4.
- **~5 GB free RAM** — 3–8B parameter models at Q4/Q5.
- **8+ GB free RAM** — larger models; quantization matters less.

If a model is too large for your device, Stella will be slow or the local
server may fail to load it. Switch to a smaller model or a cloud provider.
