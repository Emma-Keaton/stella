#!/usr/bin/env bash
# scripts/portable/portable_stella.sh — self-contained Stella launcher (Linux/macOS).
#
# Runs Stella from a fully portable layout: the .venv next to this script, the
# repo root as the working directory, and Stella's user data dir under the
# portable storage folder so nothing is written outside the bundle.
#
# Usage:
#   ./scripts/portable/portable_stella.sh
#   STELLA_DATA_DIR=~/stella-portable ./scripts/portable/portable_stella.sh

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

# Resolve the Python interpreter: prefer the venv next to this script.
py="$repo_root/.venv/bin/python"
if [[ ! -x "$py" ]]; then
    echo "No .venv found at $repo_root/.venv. Run bootstrap first." >&2
    exit 1
fi

# Portable user data: everything Stella writes stays under the portable data dir.
data_dir="${STELLA_DATA_DIR:-$script_dir/data}"
mkdir -p "$data_dir"

# Force Stella's user-data dir into the portable location.
export STELLA_USER_DATA_DIR="$data_dir"
export LOCALAPPDATA="$data_dir"

# Set the working directory to the repo so relative imports resolve.
cd "$repo_root"

echo "Stella (portable) starting from $repo_root"
echo "User data dir : $data_dir"

exec "$py" "main.py"
