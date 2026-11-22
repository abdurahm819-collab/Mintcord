#!/usr/bin/env bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "Run with sudo: sudo /opt/mintcord/installer/uninstall.sh" >&2
    exit 1
fi

rm -rf /opt/mintcord
rm -f /usr/local/bin/mintcord
rm -f /usr/share/applications/mintcord.desktop

echo "Mintcord application files removed."
echo "User data was preserved under ~/.local/share/mintcord."
echo "Remove that directory manually only if you also want to delete your local data."
