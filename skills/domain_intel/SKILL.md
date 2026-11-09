---
name: domain_intel
description: Passive and active domain intelligence: DNS records, WHOIS/RDAP registration, reverse DNS, IP geolocation and ASN ownership, subdomain enumeration through certificate-transparency logs, subdomain-takeover checks, technology fingerprinting from HTTP responses, SPF/DKIM/DMARC/CAA email-security records, passive-DNS and Wayback history, public bucket probing, and offline decoding of hashes, JWTs and packet captures. P0 passive is the default; anything that queries the target's DNS or contacts it is gated by core/tool_policy.py and names its target. Every result names its source, its key status, and its activity class.
category: osint
source: stella
version: 1.0.0
---
