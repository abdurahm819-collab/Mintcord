# Mintcord

**Free and open-source desktop messaging prototype for Linux Mint.**

## Graphical installer

From the extracted repository folder, double-click `install.sh` or run:

```bash
./install.sh
```

If the GTK 3 Python bindings are missing, the launcher first requests permission to install them, then opens the graphical installer. The installer installs Mintcord under `/opt/mintcord`, adds a desktop-menu shortcut, and includes an Uninstall option. It keeps personal settings and local data.

If double-clicking does not run the script, right-click `install.sh`, choose Properties → Permissions, and enable “Allow this file to run as a program”. You can also run it from a terminal with `bash install.sh`.

## Current interface

- Users, Chat, and Emojis tabs.
- Sample contacts and status settings.
- Local demonstration messages and simulated call windows.
- Background photos and colours.
- Desktop notifications and a local file-selection demonstration.

**Real messaging, real voice/audio, accounts, peer-to-peer networking, and encryption are not implemented yet.** Do not use this prototype for private communication.

## Run from source

```bash
python3 app/main.py
```

## Troubleshooting

If the Mintcord window does not open, run `python3 app/main.py` in a terminal to see the startup error. Also check `~/.local/share/mintcord/logs/crash.log` for the saved traceback.

## Development checks

```bash
python3 -m compileall -q app installer
bash -n install.sh installer/install_system.sh installer/uninstall_system.sh
```

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).
