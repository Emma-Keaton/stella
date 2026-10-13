#!/usr/bin/env bash
# Fetch a pinned Temurin JDK (17) for Gradle 8.7, resumable, sdkmanager-free.
# Usage:  ./scripts/fetch_jdk.sh [dest-dir]
# Default dest: ~/.local/share/stella-jdk (outside the repo, never committed).
set -euo pipefail
DEST="${1:-$HOME/.local/share/stella-jdk}"
URL="https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"
mkdir -p "$DEST"
PART="$DEST/temurin17.tar.gz.part"
OUT="$DEST/temurin17.tar.gz"
have=0
[ -f "$PART" ] && have=$(stat -c%s "$PART")
for i in $(seq 1 40); do
  if curl -fL --retry 0 -C - -o "$PART" --max-time 25 "$URL"; then
    break
  fi
  echo "retry $i (have $(stat -c%s "$PART" 2>/dev/null || echo 0) bytes)"
  sleep 5
done
mv -f "$PART" "$OUT"
tar -xzf "$OUT" -C "$DEST" --strip-components=1
"$DEST/bin/java" -version
echo "JDK ready at: $DEST"
