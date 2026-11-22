#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# The graphical installer itself needs GTK 3. If the Python bindings are
# missing, use Mint's graphical Zenity prompt to bootstrap them first.
if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    if ! command -v zenity >/dev/null 2>&1; then
        echo "Mintcord Installer cannot start: GTK 3 Python bindings are missing."
        echo "On Linux Mint, install them with:"
        echo "  sudo apt update && sudo apt install python3 python3-gi gir1.2-gtk-3.0"
        exit 1
    fi

    if ! zenity --question --title="Mintcord setup" --text="Mintcord needs GTK 3 Python support before its graphical installer can open. Install the missing components now?"; then
        exit 0
    fi

    if ! command -v pkexec >/dev/null 2>&1; then
        zenity --error --title="Mintcord setup" --text="The system authorization tool (pkexec) is unavailable. Install policykit-1, then run this installer again."
        exit 1
    fi

    if ! pkexec apt-get update || ! pkexec apt-get install -y python3 python3-gi gir1.2-gtk-3.0; then
        zenity --error --title="Mintcord setup" --text="Could not install GTK 3 Python support. Check your internet connection and try again."
        exit 1
    fi
fi

exec python3 "$SCRIPT_DIR/installer/gui_installer.py"
