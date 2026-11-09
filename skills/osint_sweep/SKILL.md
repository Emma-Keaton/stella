---
name: osint_sweep
description: Open-source intelligence sweeps across identity vectors: username enumeration across a site list, e-mail reputation and breach history, phone-number line-type and carrier, and person-name co-occurrence. Every source is classified passive (P0), DNS-based (P1) or direct-contact (P2) before it runs, and only P0 runs by default - P1 and P2 need an explicit activity class plus a policy allow rule. Each result carries a per-source outcome with its stop reason, and an empty source is reported as empty rather than as a failure.
category: osint
source: stella
version: 1.0.0
---
