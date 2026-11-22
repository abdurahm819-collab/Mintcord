#!/usr/bin/env python3
"""Entry point for the restored Mintcord v0.5 GTK prototype."""

from gi.repository import Gtk
from prototype import Mintcord


def main():
    window = Mintcord()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
