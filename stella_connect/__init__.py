"""Stella Connect subsystem.

This package adds the local gateway, device registry, pairing flow, and
protocol definitions used by Stella AI to reach companion devices.
"""

from .service import StellaConnectService, get_service

__all__ = ["StellaConnectService", "get_service"]
