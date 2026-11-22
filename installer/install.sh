#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
APP_DIR="/opt/mintcord"
USER_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/mintcord"

if [[ "$EUID" -eq 0 ]]; then
    echo "Run this installer as your normal user, not with sudo." >&2
    exit 1
fi

bash "$SCRIPT_DIR/check_system.sh"

sudo install -d -m 0755 "$APP_DIR"
sudo install -d -m 0755 "$APP_DIR/app/calling" "$APP_DIR/app/messaging" "$APP_DIR/app/networking"
sudo install -d -m 0755 "$APP_DIR/assets/icons" "$APP_DIR/assets/fonts" "$APP_DIR/assets/sounds"
sudo install -d -m 0755 "$APP_DIR/config" "$APP_DIR/server" "$APP_DIR/installer"
sudo install -d -m 0755 "$APP_DIR/tests" "$APP_DIR/docs"
sudo install -d -m 0755 "$USER_DATA_DIR" "$USER_DATA_DIR/logs"

sudo cp -a "$REPO_ROOT/app/." "$APP_DIR/app/"
sudo cp -a "$REPO_ROOT/installer/." "$APP_DIR/installer/"
sudo cp "$REPO_ROOT/README.md" "$APP_DIR/README.md"
sudo cp "$REPO_ROOT/LICENSE" "$APP_DIR/LICENSE"
sudo chown -R root:root "$APP_DIR"

sudo tee /usr/local/bin/mintcord >/dev/null <<'LAUNCHER'
#!/usr/bin/env bash
exec /usr/bin/python3 /opt/mintcord/app/main.py "$@"
LAUNCHER
sudo chmod 0755 /usr/local/bin/mintcord

sudo install -d -m 0755 /usr/share/applications
sudo tee /usr/share/applications/mintcord.desktop >/dev/null <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Mintcord
Comment=Open-source messaging prototype
Exec=/usr/local/bin/mintcord
Terminal=false
Categories=Network;Chat;
DESKTOP
sudo chmod 0644 /usr/share/applications/mintcord.desktop

echo "Mintcord prototype installed."
echo "Application: $APP_DIR"
echo "User data:   $USER_DATA_DIR"
echo "Launch with: mintcord"
echo "Note: calls and messages are currently local demonstrations only."
