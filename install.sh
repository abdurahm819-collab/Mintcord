#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# GTK is required to display the graphical installer. Bootstrap it first
# using Mint's graphical authentication prompt, then launch the real GUI.
if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    if ! command -v pkexec >/dev/null 2>&1; then
        echo "Mintcord needs GTK 3 and pkexec to install missing dependencies." >&2
        exit 1
    fi
    if command -v zenity >/dev/null 2>&1; then
        (
            pkexec apt-get update &&
            pkexec apt-get install -y python3-gi gir1.2-gtk-3.0
        ) 2>&1 | zenity --progress --title="Mintcord setup" --text="Preparing the graphical installer…" --pulsate --no-cancel --auto-close
    else
        pkexec apt-get update
        pkexec apt-get install -y python3-gi gir1.2-gtk-3.0
    fi
fi

if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    echo "GTK 3 could not be prepared. Please check your package manager." >&2
    exit 1
fi

exec python3 "$SCRIPT_DIR/installer/gui_installer.py"
