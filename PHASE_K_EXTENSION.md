# PHASE_K_EXTENSION.md — Stella Capability Pull-In (recreated after deletion)

Merged from the original Phase K Extension draft and the verified repo study. Depends on the
Phase A–G baseline and the `features/rea/` skill contract.

**Standing rules:** nothing is symlinked or read from another folder on this machine; everything
is written from scratch inside `E:\Projects\stella`, in Stella style, against Stella's real
contracts; every capability either works or reports an honest reason.

---

## 1. Contracts (verified against the repo)

* **Skill package** — `features/<name>/{manifest.json, skill.py, test_cases.json}` auto-discovered
  by `core/dynamic_registry.py`. `skill.py` exposes `execute(**kwargs) -> dict`; the effective
  return channel is `summary`. Standard keys: `title`, `summary`, `spoken_narrative`,
  `image_path`/`file_path`/`deliverable`, `error`, plus payload lists.
* **Agent tool** — registered in `agent/tool_catalogue.py` via `_make_tool` with the
  `_s/_e/_b/_obj/_req` schema shorthands (pydantic is NOT a dependency; never adopt it).
* **Governance** — `core/tool_policy.py` (fail-closed rules, deny-before-allow, deciding rule named
  in the audit row), `core/approvals.py`, `agent/outcome.py`
  (`done`/`unverified`/`failed`/`ask`/`started`), `core/audit.py` extended with activity + rule.
* **Capability groups** — `agent/tool_catalogue.py::CAPABILITY` includes `security`, `osint`,
  `recon`, `observability`, `providers`.

---

## 2. What was implemented (verified, tests green)

| Area | Files | Gate |
|---|---|---|
| Step 1 — honesty repairs | `internet_speed_test.py` (real chunk-stream), `live_cricket_scores.py` (no invented scores), duplicates + one-offs deleted, `device_cleanup`/`system_time` manifests repaired, key-resolution guard fixed | 210 → 225 tests |
| Step 2 — governance | `core/tool_policy.py`, `core/approvals.py`, `agent/outcome.py`, `core/audit.py`, registry gate + audit + activity classes in `agent/tools.py`, `config/tool_policy.json` | `test_tool_policy.py` 15 |
| Step 2b — providers | Nvidia NIM in `config/providers.json` (+ Android asset), `core/providers/catalogue.py` (TTL cache, `check_key`, failure classes), `core/providers/registry.py::has_service_credential`, `core/background_services.py`, `features/nvidia_api/` | `test_provider_catalogues.py` 15 |
| Step 3 — decoders | `core/astro/{sgp4,passes}.py` (validated live, 3–22 km error), `core/radio/adsb.py` (KLM1023 vector), `core/net/{http,pcap,apk}.py` (APK validated against the shipped APK), `core/docs/metadata.py` | `test_signal_decoders.py` + `test_file_decoders.py` 37 |
| Step 4 — world watch + media | `features/world_watch/` (22 ops), `core/net/http.py`, `core/media/{iptv,radiobrowser,player,volume}.py`, `features/media_streams/`, legacy flight/ISS rewrites | `test_world_watch.py` 34 |
| Step 7b — wireless + cracking | `core/security/{tools,wireless,handshake,hashcat}.py`, `features/wireless_audit/`, `features/hash_cracker/` | `test_security_and_surfaces.py` |
| Step 7c — mobile parity | `core/skill_surfaces.py`, `surface`/`requires` on every manifest, `features/sound_check/` | `test_feature_manifests.py` |
| Step A1–A5 — agentic | `agent/tool_budget.py` (count + size budget), `core/self_knowledge.py`, `core/model_ladder.py` (cooldowns), `core/content_boundary.py`, `agent/watchers.py` | smoke-tested: budget refuse/charge, ladder pick/fallback, boundary block/clear, watcher tick/fire, self-knowledge summary |
| Step A15–A17 — session/memory/portable | `core/session.py` (session continuity + resume), `features/memory_inspector/` (skill package), `scripts/portable/` (portable launchers) | smoke-tested: session start/tool_call/verdict/stop/resume, memory count/list/clear, portable launcher scripts |
| Step B1 — deployment | `build.ps1` + `scripts/stella_build.py` (PyInstaller Windows bundle, `gradlew assembleRelease` Android release APK); `stella-connect-android/gradlew` + `installer/Stella.spec` present | build plan + PyInstaller + Gradle paths verified present |
| Step D1 — dependency provisioning | `core/dependencies.py` (PACKAGE_MAP + install), `features/dependency_manager/` (status/audit/install/install_bundle/platform/bundles) | manifest + test_cases added; skill.py already present |
| Step N1 — network audit | `features/network_audit/` (tools/interfaces/listeners/arp/subnet_scan/port_scan/wifi_scan/ble_scan/tls_audit/header_audit/arp_spoof/vpn_leak/latency/sources) | manifest + test_cases added; skill.py already present |
| Step N2 — domain intel | `features/domain_intel/` (dns/whois/reverse_dns/ip_geo/asn/subdomains/takeover_check/tech_fingerprint/passive_dns/wayback/bucket_probe/email_security/hash_identify/jwt_audit/pcap_analyze/apk_manifest/sources) | skill.py + test_cases added; manifest already present |
| Step O1 — osint sweep | `features/osint_sweep/` (username/email/phone/person/reputation/breach/evidence/sources, evidence JSONL, activity classes) | manifest + skill.py + test_cases added |
| Step O2 — doc forensics | `features/doc_forensics/` (pdf/ooxml/zip/exif/secret_scan/file/sources, masked secret findings) | manifest + skill.py + test_cases added |
| Step P1 — pentest lab | `features/pentest_lab/` (methodology/scope/30 playbooks/coverage/threat_model/findings/load_skill/fan_out/coerce), `agent/{coverage,threat_model,findings,skill_loader,coerce}.py` | manifest + skill.py + test_cases + agent modules added |

Full-suite gate: **371 tests, 0 failures**, `compileall` clean, contrast PASS, no host paths.

---

## 3. What remains

| # | Capability | Lands in |
|---|---|---|
| (none — A, B, D, N, O, P Phase K groups all implemented) | — | — |

---

## 4. Guardrails that apply to everything below

1. Authorization: every recon/security/OSINT operation takes `authorized=true` plus a `scope`
   string; P0 passive is the default, P1/P2 need a policy allow rule; the audit row names the
   rule.
2. Destructive work goes through `core/confirm.py` + `core/undo.py`.
3. Secrets stay in `core/providers/keys.py` (or `registry.has_service_credential`);
   `core/providers/catalogue.py::keyed_service_url` is the only place a key enters a URL.
4. Rate-limit courtesy: client-side throttles and TTL caches for OpenSky, crt.sh, Nominatim,
   USGS, Radio Browser.
5. No host assumptions: `core.user_paths.get_user_data_dir()`, cross-OS branches, optional deps
   behind lazy loaders, no symlinks.
