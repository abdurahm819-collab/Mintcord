#!/usr/bin/env python3
"""Mintcord prototype v0.2 - GTK interface with simulated calls.

This is the original UI foundation. Sample contacts, messages, and call
states are local demonstrations; there is no networking or real audio.
"""
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

APP_NAME = "Mintcord"
ANSWER_DELAY = 10

TEST_USERS = [
    ("Alice", "user-available", "Online"),
    ("Bob", "user-away", "Away"),
    ("Carol", "user-busy", "Busy"),
    ("Dave", "user-idle", "Idle"),
    ("Eve", "user-invisible", "Invisible"),
    ("Frank", "user-offline", "Offline"),
]
QUEUED_ICONS = {"user-offline", "user-invisible"}
NO_ANSWER_ICONS = {"user-offline", "user-invisible"}


def big_button(icon, text, size=96):
    btn = Gtk.Button()
    btn.set_relief(Gtk.ReliefStyle.NONE)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
    img.set_pixel_size(size)
    box.pack_start(img, False, False, 0)
    box.pack_start(Gtk.Label(label=text), False, False, 0)
    btn.add(box)
    return btn


class CallWindow(Gtk.Window):
    """Demonstration call window; does not connect to another computer."""

    def __init__(self, parent, name, icon, incoming):
        super().__init__(title=f"Call - {name}")
        self.set_transient_for(parent)
        self.set_default_size(380, 380)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.icon = icon
        self.seconds = 0
        self.sources = set()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(20)
        self.add(box)

        who = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        who.pack_start(
            Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR),
            False, False, 0
        )
        title = Gtk.Label()
        title.set_markup(f"<big><b>{GLib.markup_escape_text(name)}</b></big>")
        who.pack_start(title, False, False, 0)
        box.pack_start(who, False, False, 0)

        self.status = Gtk.Label()
        box.pack_start(self.status, False, False, 0)

        self.btn_box = Gtk.Box(
            spacing=40, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER
        )
        box.pack_start(self.btn_box, True, True, 0)

        if incoming:
            self.status.set_text("Demo incoming call...")
            self._show_incoming()
        else:
            self.status.set_text("Demo calling...")
            self._show_stop()
            self._after(ANSWER_DELAY, self._npc_answers)

        self.connect("destroy", self._cleanup)

    def _clear_buttons(self):
        for child in self.btn_box.get_children():
            self.btn_box.remove(child)

    def _show_stop(self):
        self._clear_buttons()
        stop = big_button("call-stop", "End demo", 128)
        stop.connect("clicked", lambda _b: self.destroy())
        self.btn_box.pack_start(stop, False, False, 0)
        self.btn_box.show_all()

    def _show_incoming(self):
        self._clear_buttons()
        accept = big_button("call-start", "Accept demo")
        accept.connect("clicked", lambda _b: self._connected())
        deny = big_button("call-stop", "Dismiss")
        deny.connect("clicked", lambda _b: self.destroy())
        self.btn_box.pack_start(accept, False, False, 0)
        self.btn_box.pack_start(deny, False, False, 0)
        self.btn_box.show_all()

    def _npc_answers(self):
        if self.icon in NO_ANSWER_ICONS:
            self.status.set_text("Demo: no answer")
        else:
            self._connected()

    def _connected(self):
        self._update_time()
        self._show_stop()
        self.sources.add(GLib.timeout_add_seconds(1, self._tick))

    def _tick(self):
        self.seconds += 1
        self._update_time()
        return True

    def _update_time(self):
        minutes, seconds = divmod(self.seconds, 60)
        self.status.set_text(f"Demo connected  {minutes:02d}:{seconds:02d}")

    def _after(self, seconds, fn):
        holder = []

        def run():
            self.sources.discard(holder[0])
            fn()
            return False

        holder.append(GLib.timeout_add_seconds(seconds, run))
        self.sources.add(holder[0])

    def _cleanup(self, _widget):
        for source_id in self.sources:
            GLib.source_remove(source_id)
        self.sources.clear()


class Mintcord(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)
        self.set_default_size(520, 480)
        self.set_icon_name("user-info")
        self.buffers = {}
        self.current = None
        self.call_win = None

        self.notebook = Gtk.Notebook()
        self.add(self.notebook)
        self.notebook.append_page(
            self._build_users_tab(), Gtk.Label(label="Users")
        )
        self.notebook.append_page(
            self._build_chat_tab(), Gtk.Label(label="Chat")
        )

    def _build_users_tab(self):
        listbox = Gtk.ListBox()
        listbox.set_activate_on_single_click(False)
        for name, icon, status in TEST_USERS:
            listbox.add(self._make_row(name, icon, status))
        listbox.connect("row-activated", self._on_row_activated)

        scroll = Gtk.ScrolledWindow()
        scroll.add(listbox)
        return scroll

    def _make_row(self, name, icon, status):
        row = Gtk.ListBoxRow()
        row.user = (name, icon)

        events = Gtk.EventBox()
        events.add_events(
            Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        box = Gtk.Box(spacing=10)
        box.set_border_width(6)
        box.pack_start(
            Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR),
            False, False, 0
        )

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        name_label = Gtk.Label(xalign=0)
        name_label.set_markup(f"<b>{GLib.markup_escape_text(name)}</b>")
        status_label = Gtk.Label(label=status, xalign=0)
        status_label.get_style_context().add_class("dim-label")
        text.pack_start(name_label, False, False, 0)
        text.pack_start(status_label, False, False, 0)
        box.pack_start(text, True, True, 0)

        pov = Gtk.Button(label="Demo")
        pov.set_relief(Gtk.ReliefStyle.NONE)
        pov.set_tooltip_text(f"Show a simulated incoming call from {name}")
        pov.connect(
            "clicked",
            lambda _b: self._open_call(name, icon, incoming=True)
        )
        box.pack_end(pov, False, False, 0)

        call = Gtk.Button()
        call.set_image(
            Gtk.Image.new_from_icon_name("call-start", Gtk.IconSize.BUTTON)
        )
        call.set_relief(Gtk.ReliefStyle.NONE)
        call.set_tooltip_text(f"Simulate calling {name}")
        call.set_opacity(0)
        call.connect(
            "clicked",
            lambda _b: self._open_call(name, icon, incoming=False)
        )
        box.pack_end(call, False, False, 0)

        events.connect(
            "enter-notify-event", lambda _w, _e: call.set_opacity(1)
        )
        events.connect("leave-notify-event", self._on_leave, call)

        events.add(box)
        row.add(events)
        return row

    @staticmethod
    def _on_leave(_widget, event, call_button):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return
        call_button.set_opacity(0)

    def _on_row_activated(self, _listbox, row):
        name, icon = row.user
        self._open_chat(name, icon)

    def _open_call(self, name, icon, incoming):
        if self.call_win is not None:
            self.call_win.present()
            return
        self.call_win = CallWindow(self, name, icon, incoming)
        self.call_win.connect(
            "destroy", lambda _w: setattr(self, "call_win", None)
        )
        self.call_win.show_all()

    def _build_chat_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(6)

        header = Gtk.Box(spacing=6)
        self.peer_icon = Gtk.Image.new_from_icon_name(
            "user-info", Gtk.IconSize.LARGE_TOOLBAR
        )
        self.peer_label = Gtk.Label(
            label="Pick a sample user (double-click)"
        )
        header.pack_start(self.peer_icon, False, False, 0)
        header.pack_start(self.peer_label, False, False, 0)
        box.pack_start(header, False, False, 0)

        self.text_view = Gtk.TextView(
            editable=False, wrap_mode=Gtk.WrapMode.WORD
        )
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.text_view)
        box.pack_start(scroll, True, True, 0)

        row = Gtk.Box(spacing=6)
        self.entry = Gtk.Entry()
        self.entry.connect("activate", self._on_send)
        send = Gtk.Button(label="Send demo")
        send.connect("clicked", self._on_send)
        row.pack_start(self.entry, True, True, 0)
        row.pack_start(send, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    def _open_chat(self, name, icon):
        self.current = (name, icon)
        if name not in self.buffers:
            self.buffers[name] = Gtk.TextBuffer()
        self.text_view.set_buffer(self.buffers[name])
        self.peer_icon.set_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
        self.peer_label.set_text(name)
        self.notebook.set_current_page(1)
        self.entry.grab_focus()

    def _on_send(self, _widget):
        message = self.entry.get_text().strip()
        if not message or not self.current:
            return
        name, icon = self.current
        buffer = self.buffers[name]
        suffix = " (local demo; not delivered)" if icon in QUEUED_ICONS else " (local demo)"
        buffer.insert(buffer.get_end_iter(), f"You: {message}{suffix}\n")
        self.entry.set_text("")


def main():
    window = Mintcord()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
