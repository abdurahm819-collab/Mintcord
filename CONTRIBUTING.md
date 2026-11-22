# Contributing to Mintcord

Thank you for considering a contribution.

## Before opening a pull request

1. Check existing issues to avoid duplicate work.
2. Explain the problem and the proposed change.
3. Keep changes focused and document new behavior.
4. Add tests where practical.
5. Do not claim that networking, encryption, or calling works unless it is implemented and tested.

## Development

The current desktop prototype requires Linux Mint (or a compatible GTK 3 desktop) with Python 3 and PyGObject installed.

Run:

```bash
python3 app/main.py
```

## Security-sensitive changes

Changes involving cryptography, identity, peer discovery, network transport, or audio capture require extra review. Do not invent cryptographic protocols or roll your own encryption. Prefer established, maintained implementations and document their threat model and limitations.

By submitting a contribution, you agree that it is provided under the project's GPL-3.0 license, subject to the rights you hold in that contribution.
