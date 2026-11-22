#!/usr/bin/env bash
set -euo pipefail
if [[ "$EUID" -ne 0 ]]; then echo "Run this helper through pkexec." >&2; exit 1; fi
SOURCE_DIR="${1:-}"
if [[ -z "$SOURCE_DIR" || ! -f "$SOURCE_DIR/app/main.py" || ! -f "$SOURCE_DIR/LICENSE" ]]; then
    echo "Invalid Mintcord source directory." >&2; exit 2
fi
APP_DIR="/opt/mintcord"
install -d -m 0755 "$APP_DIR" "$APP_DIR/app" "$APP_DIR/installer" "$APP_DIR/assets"
cp -a "$SOURCE_DIR/app/." "$APP_DIR/app/"
cp -a "$SOURCE_DIR/installer/." "$APP_DIR/installer/"
cp "$SOURCE_DIR/README.md" "$SOURCE_DIR/LICENSE" "$APP_DIR/"
if [[ -f "$SOURCE_DIR/assets/mintcord.svg" ]]; then cp "$SOURCE_DIR/assets/mintcord.svg" "$APP_DIR/assets/"; fi
chown -R root:root "$APP_DIR"
cat > /usr/local/bin/mintcord <<'LAUNCHER'
#!/usr/bin/env bash
exec /usr/bin/python3 /opt/mintcord/app/main.py "$@"
LAUNCHER
chmod 0755 /usr/local/bin/mintcord
install -d -m 0755 /usr/share/applications
cat > /usr/share/applications/mintcord.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Mintcord
Comment=Open-source desktop messaging prototype
Exec=/usr/local/bin/mintcord
Icon=/opt/mintcord/assets/mintcord.svg
Terminal=false
Categories=Network;Chat;
StartupNotify=true
DESKTOP
chmod 0644 /usr/share/applications/mintcord.desktop
echo "Mintcord installed successfully."
