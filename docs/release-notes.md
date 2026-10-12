# Release notes — Stella Connect (Android)

Per-edition notes for the Android companion app. Built and published by
GitHub Actions on every `v*`-tagged git release.

## What ships on an Android release

| Edition | File | Contents | Signature |
|---|---|---|---|
| **Private** | `Stella-Connect-1.0.0-android-k2.apk` | K2-bundled: local model + llama-server + services. Works out of the box. | Signed with `CN=Stella Local` (personal keystore) → in-place upgrades |
| **Public** | `Stella-Connect-1.0.0-android.apk` | No model bundled. Sideloadable anywhere. | Unsigned by design (no keystore shipped) |

Both APKs are assembled by the same Gradle `assembleRelease` task. The public
APK is left unsigned so it can be sideloaded on any machine; the private K2 APK
is signed with the per-user keystore `~/.stella-toolchain/stella-personal.jks`
so the same key keeps upgrades installing over the previous one.

## How to build

```powershell
# Private (K2-bundled) — auto-mints/releases stella-personal.jks in
# ~/.stella-toolchain and signs with it.
python scripts\stella_build.py --edition core --os android --k2 --release

# Public — unsigned, user picks a compatible model in-app.
python scripts\stella_build.py --edition core --os android --release
```

## Versioning

- The APK name carries the version: `Stella-Connect-{version}-android-k2.apk`
  / `Stella-Connect-{version}-android.apk` (read from `app_version.txt` or
  `version.txt`).
- GitHub Releases are created from any `v*` tag. CI merges per-build
  `dist/manifest.json` entries into a single `manifest.json` and ships every
  artifact (`*.apk`, `*.zip`, `*.exe`, `*.AppImage`, `*.dmg`) in one release.
