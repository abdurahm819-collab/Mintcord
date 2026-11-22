#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    echo "The graphical installer needs GTK 3 Python bindings."
    echo "Install them once with:"
    echo "  sudo apt update"
    echo "  sudo apt install python3 python3-gi gir1.2-gtk-3.0"
    exit 1
fi
exec python3 "$SCRIPT_DIR/installer/gui_installer.py"
