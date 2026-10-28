#!/usr/bin/env bash
# Stella Android permission grant/revoke script
# Usage:
#   bash grant_stella_permissions_android.sh grant
#   bash grant_stella_permissions_android.sh revoke
#   bash grant_stella_permissions_android.sh grant PERMISSION_NAME
#   bash grant_stella_permissions_android.sh revoke PERMISSION_NAME
set -euo pipefail

PACKAGE="com.stella.connect"
PERMS=(
  "android.permission.CAMERA"
  "android.permission.RECORD_AUDIO"
  "android.permission.POST_NOTIFICATIONS"
  "android.permission.ACCESS_FINE_LOCATION"
  "android.permission.ACCESS_COARSE_LOCATION"
  "android.permission.FOREGROUND_SERVICE"
  "android.permission.FOREGROUND_SERVICE_MICROPHONE"
  "android.permission.FOREGROUND_SERVICE_CAMERA"
  "android.permission.WRITE_EXTERNAL_STORAGE"
  "android.permission.READ_EXTERNAL_STORAGE"
  "android.permission.MANAGE_EXTERNAL_STORAGE"
  "android.permission.SYSTEM_ALERT_WINDOW"
  "android.permission.BIND_ACCESSIBILITY_SERVICE"
  "android.permission.USE_FULL_SCREEN_INTENT"
)

action=${1:-}
perm=${2:-}

check_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    echo "adb not found"
    exit 1
  fi
  if ! adb devices | grep -q "device$"; then
    echo "No device connected"
    exit 1
  fi
}

grant_one() {
  local p=$1
  echo "Granting $p"
  adb shell pm grant "$PACKAGE" "$p" || echo "Note: $p may require user approval"
}

revoke_one() {
  local p=$1
  echo "Revoking $p"
  adb shell pm revoke "$PACKAGE" "$p" || true
}

check_adb

if [[ "$action" == "grant" && -z "$perm" ]]; then
  for p in "${PERMS[@]}"; do grant_one "$p"; done
elif [[ "$action" == "revoke" && -z "$perm" ]]; then
  for p in "${PERMS[@]}"; do revoke_one "$p"; done
elif [[ "$action" == "grant" && -n "$perm" ]]; then
  grant_one "$perm"
elif [[ "$action" == "revoke" && -n "$perm" ]]; then
  revoke_one "$perm"
else
  echo "Usage: $0 grant|revoke [PERMISSION]"
  exit 1
fi
echo "Done"
