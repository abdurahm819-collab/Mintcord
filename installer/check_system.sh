#!/usr/bin/env bash
set -euo pipefail

missing=()
for command in python3 dpkg-query; do
    command -v "$command" >/dev/null 2>&1 || missing+=("$command")
done

if (("${#missing[@]}" > 0)); then
    printf 'Missing required commands: %s\n' "${missing[*]}" >&2
    exit 1
fi

if ! grep -qi 'linux mint' /etc/os-release; then
    echo "Warning: this installer is designed for Linux Mint." >&2
fi

packages=(python3-gi gir1.2-gtk-3.0)
missing_packages=()
for package in "${packages[@]}"; do
    if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        missing_packages+=("$package")
    fi
done

if (("${#missing_packages[@]}" > 0)); then
    printf 'Missing packages: %s\n' "${missing_packages[*]}"
    read -r -p "Install these packages with apt? [y/N] " answer
    case "$answer" in
        y|Y|yes|YES)
            sudo apt-get update
            sudo apt-get install -y "${missing_packages[@]}"
            ;;
        *)
            echo "Cannot continue without the GTK 3 Python bindings." >&2
            exit 1
            ;;
    esac
fi

python3 - <<'PY'
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
print("Python and GTK 3 checks passed.")
PY
