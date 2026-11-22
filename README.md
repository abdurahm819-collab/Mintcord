# Mintcord

**Free and open-source desktop messaging prototype for Linux Mint.**

Mintcord is a Python 3 + GTK 3 desktop application. The project currently uses the restored **v0.5 interface** from the original prototype. It is a local GUI demonstration, not yet a network messaging or calling service.

## Current interface features

- Users, Chat, and Emojis tabs.
- Sample contacts with Online, Away, Busy, Idle, Invisible, and Offline statuses.
- Simulated incoming and outgoing call windows.
- A microphone button that toggles the interface's mute indicator.
- Status settings, per-status notification preferences, and automatic-reply text.
- Main-window, all-chat, and per-chat photo backgrounds.
- Per-chat background colours.
- Desktop message notifications for simulated incoming messages.
- File chooser that records a selected file in the local chat UI.
- Settings saved in `~/.config/mintcord/settings.json`.

## Important: what does not work yet

The current version does **not** provide real communication:

| Feature | Current state |
|---|---|
| Contacts | Sample users only |
| Chat messages | Local demonstration; not sent to another computer |
| Incoming messages | Simulated test events |
| Voice calls | Simulated call windows; no audio or network connection |
| Microphone mute | Changes the UI mute flag only; no microphone capture exists |
| File sending | Selects a local file and adds a local chat entry; no transfer occurs |
| Accounts / sign-in | Not implemented |
| Peer-to-peer networking | Not implemented |
| Encryption | Not implemented |

Do not use this prototype for private or sensitive communication. Do not interpret the call timer or microphone indicator as evidence that a real call or audio session exists.

## Requirements

- Linux Mint or another GTK 3 desktop
- Python 3
- PyGObject with GTK 3, GDK 3, and GdkPixbuf 2 bindings

On Linux Mint, install the system dependencies with:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0
```

## Run from source

From the repository root:

```bash
python3 app/main.py
```

The main interface source is `app/prototype.py`.

## Install

From the repository root:

```bash
./install.sh
```

The installer checks for the required GTK/Python packages and installs the application under `/opt/mintcord`. It creates a desktop launcher named Mintcord.

To uninstall:

```bash
sudo /opt/mintcord/installer/uninstall.sh
```

The uninstall script preserves user data under the home directory.

## Development checks

Check Python syntax without launching the GUI:

```bash
python3 -m compileall -q app
```

The GTK interface must be launched on a graphical GTK 3 desktop for a manual UI test.

## Project direction

The next major development stage is real messaging and voice calling. The planned direction is peer-to-peer communication where network conditions allow, with established protocols and maintained libraries for transport and encryption. Direct peer-to-peer connections are not guaranteed on every network and may require signaling and relay infrastructure.

No networking, audio transport, or encryption is included in this release.

## License

Mintcord is free and open-source software under the GNU General Public License v3.0. See [LICENSE](LICENSE).
