Stella bundles a modified copy of cactus-needle.

Upstream  : https://github.com/cactus-compute/needle
Licence   : Apache License 2.0 (see LICENSE-APACHE-2.0.txt)
Copied by : scripts/vendor_needle.py

Modifications made by Stella
----------------------------
1. needle/_telemetry.py is a deliberate no-op. Upstream reports anonymous
   usage counts to a remote endpoint on every call unless the user opts out.
   Stella ships an air-gapped offline mode, so no telemetry is collected or
   transmitted from this copy at all. `track()` is kept as a stub because
   needle/__init__.py imports it.

2. Only the runtime subset is vendored. Omitted: cli.py, mcp_server.py,
   openai_server.py, playground/, platform.py, and model/ (training, export,
   quantisation, tokenizer). Those pull torch and a tokenizer blob and are
   not needed to run tool calls.

3. No source file in this copy has been edited otherwise; the files here are
   byte-identical to upstream except where noted above.

The full unmodified upstream sources remain the authoritative reference.
