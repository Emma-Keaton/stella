---
name: network_audit
description: Audits the network this machine is attached to: interfaces, routes and gateways, listening sockets, the ARP table, parallel host discovery on a subnet, parallel port scanning with service identification, a TLS handshake audit (protocol versions, cipher suites, certificate chain and expiry), an HTTP security-header audit, Wi-Fi and BLE beacon sweep, ARP-spoofing detection and a VPN-leak check. Read-only by default; anything that contacts a named target is gated by core/tool_policy.py and names its target. Never scans a network the caller did not name.
category: security
source: stella
version: 1.0.0
---
