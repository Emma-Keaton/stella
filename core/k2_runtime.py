# -*- coding: utf-8 -*-
"""Deprecated module path for the local-engine runtime contract.

The file was renamed ``k2_runtime`` -> ``engine_runtime`` because it no longer
describes one model family: it carries BOTH llama-server runtime definitions
(upstream llama.cpp + the MBZUAI/K2Horizon fork), the GGUF architecture
sniffer that routes a model to the right server, and the ``server_*`` settings
keys. Everything is re-exported here so legacy ``from core import k2_runtime``
imports keep working; new code should import ``core.engine_runtime``.
"""
from __future__ import annotations

from core.engine_runtime import *  # noqa: F401,F403 - re-export every public name
from core.engine_runtime import _skip_gguf_value  # noqa: F401 - used by tests
