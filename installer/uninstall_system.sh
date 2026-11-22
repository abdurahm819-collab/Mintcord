#!/usr/bin/env bash
set -euo pipefail
if [[ "$EUID" -ne 0 ]]; then echo "Run this helper through pkexec." >&2; exit 1; fi
rm -f /usr/local/bin/mintcord /usr/share/applications/mintcord.desktop
rm -rf /opt/mintcord
echo "Mintcord application files removed. User settings and data were preserved."
