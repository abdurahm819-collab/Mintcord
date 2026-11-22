# Mintcord

**Free and open-source desktop messaging and voice-calling project for Linux Mint.**

Mintcord is an early-stage Python/GTK application. The current interface is a prototype: its sample contacts, chat messages, and call states are local demonstrations. Real networking, peer discovery, and voice calling are **not implemented yet**.

## Project goals

- Native Linux Mint desktop experience using GTK 3.
- Peer-to-peer communication where network conditions permit.
- Encrypted voice communication using established, audited protocols and libraries.
- No phone-number requirement.
- A self-contained installer with dependency and desktop-integration checks.
- No dependency on the user's icon or emoji theme for essential controls.
- Free and open-source development under GPL-3.0.

## Current status

| Feature | Status |
|---|---|
| GTK 3 prototype interface | Available |
| Sample contacts and local chat UI | Demonstration only |
| Real user accounts | Not implemented |
| Network messaging | Not implemented |
| Peer-to-peer signaling / discovery | Not implemented |
| Real voice calls | Not implemented |
| Audio encryption | Not implemented |
| Installer and uninstaller | Initial development scripts |

Do not use this prototype for private or sensitive communication. It does not currently transmit messages or calls between computers.

## Requirements

- Linux Mint (GTK 3 desktop)
- Python 3
- PyGObject / GTK 3 bindings

On Linux Mint, the GTK bindings are normally supplied by the system packages:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0
```

## Run from source

```bash
python3 app/main.py
```

## Install

From the repository root:

```bash
./install.sh
```

The installer checks for Linux Mint and required GTK/Python components, asks before installing missing system packages, and creates the application directory layout. It uses `/opt/mintcord` for application files and keeps user data under the user's home directory.

Uninstall:

```bash
sudo /opt/mintcord/installer/uninstall.sh
```

User data is preserved unless explicitly removed.

## Security and privacy

The current prototype has no network transport and no end-to-end encryption implementation. Security claims will only be made after the relevant protocols are implemented, tested, and independently reviewed. See [SECURITY.md](SECURITY.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and carefully scoped contributions are welcome.

## License

Mintcord is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
