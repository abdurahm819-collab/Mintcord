# Mintcord

**Free and open-source desktop messaging prototype for Linux Mint.**

## Graphical installer

From the extracted repository folder, double-click `install.sh` or run:

```bash
./install.sh
```

The graphical installer checks the required Python/GTK packages, requests administrator permission only when needed, installs Mintcord to `/opt/mintcord`, and adds Mintcord to the application menu. The Uninstall button removes application files while preserving user settings and local data.

If the graphical installer cannot start because GTK's Python bindings are missing, run this one-time bootstrap command:

```bash
sudo apt update && sudo apt install python3 python3-gi gir1.2-gtk-3.0
```

## Run from source

```bash
python3 app/main.py
```

## Current application status

The v0.5 interface includes sample contacts, local demonstration chats, simulated call windows, settings, backgrounds, emojis, and desktop notifications. Real network messaging, real microphone/audio, file transfer, accounts, peer-to-peer discovery, and encryption are **not implemented yet**. Do not use this prototype for private communication.

## Dependencies

- Python 3
- PyGObject / GTK 3
- Linux Mint or another GTK 3 desktop

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).
