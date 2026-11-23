#!/usr/bin/env python3
"""Entry point for the Mintcord v0.5 GTK prototype.

If the window does not open, the reason is written to
~/.local/share/mintcord/logs/crash.log (and printed in the terminal).
"""
import os
import sys
import traceback


def main():
    import gi

    # Pin GTK 3 BEFORE anything imports Gtk. Without this, PyGObject loads the
    # newest Gtk installed (GTK 4 on some Mint setups) and the GTK 3 prototype
    # then crashes with "Namespace Gtk is already loaded with version 4.0".
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import Gtk

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from prototype import Mintcord

    window = Mintcord()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


def log_crash():
    text = traceback.format_exc()
    sys.stderr.write(text)
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    try:
        log_dir = os.path.join(data_home, "mintcord", "logs")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "crash.log"), "w") as f:
            f.write(text)
    except OSError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_crash()
        sys.exit(1)
