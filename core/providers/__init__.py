"""core/providers - shared cloud provider infrastructure.

Modules:
    registry  - loads config/providers.json (the single source of truth)
    keys      - the ONE place an API key is resolved (T1.11)
    adapters  - per-provider wire formats (openai / anthropic)
    router    - ProviderRouter: resolves a mode to an ordered provider chain
"""
