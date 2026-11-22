#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required but was not found." >&2
    exit 1
fi

# Bootstrap GTK before starting the GTK-based installer. This is necessary
# on fresh Mint/Ubuntu installations where the Python GTK bindings are absent.
if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    if ! command -v pkexec >/dev/null 2>&1; then
        echo "Mintcord needs GTK 3, but pkexec is unavailable to install it." >&2
        echo "Install PolicyKit support, then run ./install.sh again." >&2
        exit 1
    fi
    echo "Installing the small GTK 3 runtime needed to open Mintcord's graphical installer..."
    pkexec apt-get update
    pkexec apt-get install -y python3-gi gir1.2-gtk-3.0
fi

exec python3 "$SCRIPT_DIR/installer/gui_installer.py"
