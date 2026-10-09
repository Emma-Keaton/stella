# Stella on iOS — future plan (not a build yet)

> Status: **planned**. No Xcode project exists in this repo and no Apple
> toolchain runs on Windows, so `--os ios` plans honestly and refuses to
> fake a build. This doc is the checklist that turns the plan into a build.

## Why iOS is different from Android

Android ships an unsigned `.apk` you can sideload onto your own phone in
seconds. Apple allows no equivalent: a real iOS app needs macOS + Xcode, a
SwiftUI (or Flutter/React-Native) shell app, an Apple Developer account
($99/yr) for device installs, and TestFlight or the App Store for
distribution. No script on a Windows PC can conjure that — so the plan is
explicit about the gate instead of pretending.

## Checklist to ship it

1. **Shell app** — new `stella-connect-ios/` SwiftUI project. It reuses the
   same backend contract as the Android companion: pair by QR, WebSocket to
   the desktop gateway (`stella_connect/gateway/`), same message schema.
2. **Mac or CI** — build with `xcodebuild -scheme Stella archive` on a Mac,
   or add an `ios` job to `.github/workflows/build-release.yml` running on
   `macos-latest` (Apple's cloud Macs; legitimate and works today).
3. **Signing** — Apple Developer team + provisioning profile, stored as CI
   secrets (`IOS_CERTIFICATE_P12`, `IOS_PROVISIONING_PROFILE`).
4. **Distribution** — TestFlight internal track first (your own iPhone in
   minutes), App Store later. Enterprise/ad-hoc `.ipa` for side-load-like
   flows where policy allows.
5. **Wire into `stella_build.py`** — replace the current `ios` guard's
   `return 2` with a `_build_ios()` that shells out to `xcodebuild` and
   drops the `.ipa` into `dist/` + `manifest.json`, same as the APK path.

## Interim (today)

- Desktop + Android cover daily use; the APK sideloads to your phone now.
- `python scripts/stella_build.py --edition core --os ios --plan` shows the
  honest state and points here.
