#!/usr/bin/env python3
"""Mintcord prototype v0.5 - GUI shell with fake calls, mic mute, emojis,
file sending, notifications, photo/colour backgrounds and a settings window
(status, per-status actions, auto-replies).

Uses the system's stock icon theme names for interface controls.
Settings are saved in ~/.config/mintcord/settings.json.
"""
import json
import os
import random

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

APP_NAME = "Mintcord"
ANSWER_DELAY = 10
TEST_MESSAGE_DELAY = 5
CONFIG = os.path.join(GLib.get_user_config_dir(), "mintcord", "settings.json")
MAIN_KEY = "__main__"
CHATS_KEY = "__chats__"

# (name, stock icon name, status label)
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
TEST_MESSAGES = [
    "Hey, you there?", "Want to hop on a call?", "Check this out!",
    "lol did you see that?", "Are you free later?",
]

STATUSES = [
    ("Online", "user-available"),
    ("Away", "user-away"),
    ("Busy", "user-busy"),
    ("Idle", "user-idle"),
    ("Invisible", "user-invisible"),
    ("Offline", "user-offline"),
]
STATUS_ICON = dict(STATUSES)
DEFAULT_AUTO = {
    "Online": "",
    "Away": "Hey, I'm away right now. I'll reply when I'm back.",
    "Busy": "Hey, I'm busy, I can't talk now.",
    "Idle": "I'm idle at the moment, I'll get back to you soon.",
    "Invisible": "",
    "Offline": "",
}
DEFAULT_NOTIFY = {
    "Online": True, "Away": True, "Busy": False,
    "Idle": True, "Invisible": True, "Offline": False,
}

EMOJIS = [
    "face-angel", "face-angry", "face-cool", "face-crying", "face-devilish",
    "face-embarrassed", "face-glasses", "face-kiss", "face-laugh", "face-monkey",
    "face-plain", "face-raspberry", "face-sad", "face-sick", "face-smile",
    "face-smile-big", "face-smirk", "face-surprise", "face-tired",
    "face-uncertain", "face-wink", "face-worried",
]


def theme_icon(*names):
    """First icon name that exists in the current theme."""
    theme = Gtk.IconTheme.get_default()
    for name in names:
        if theme.has_icon(name):
            return name
    return names[-1]


def to_hex(rgba):
    return "#{:02x}{:02x}{:02x}".format(
        round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255))


def text_color_for(hex_color):
    """Black or white text, whichever is readable on this background."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#000000" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#ffffff"


def human_size(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def usable_image(path):
    return path if path and os.path.isfile(path) else None


class Settings:
    """Status, per-status actions, auto-reply text, colours and photos."""

    def __init__(self):
        self.data = {
            "status": "Online",
            "auto": dict(DEFAULT_AUTO),
            "notify": dict(DEFAULT_NOTIFY),
            "backgrounds": {},
            "images": {},
        }
        try:
            with open(CONFIG) as file:
                saved = json.load(file)
            if saved.get("status") in STATUS_ICON:
                self.data["status"] = saved["status"]
            for key in ("auto", "notify", "backgrounds", "images"):
                if isinstance(saved.get(key), dict):
                    self.data[key].update(saved[key])
        except (OSError, ValueError, AttributeError):
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
            with open(CONFIG, "w") as file:
                json.dump(self.data, file, indent=2)
        except OSError:
            pass


class ImageBackground(Gtk.DrawingArea):
    """Paints a photo scaled to cover the area, with a dark layer for readability."""

    def __init__(self):
        super().__init__(hexpand=True, vexpand=True)
        self.path = None
        self.pixbuf = None
        self._cache = (None, None)
        self.connect("draw", self._on_draw)

    def set_image(self, path):
        if path == self.path:
            return
        self.path = path
        self.pixbuf = None
        self._cache = (None, None)
        if path:
            try:
                self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 1920, 1920, True)
            except GLib.Error:
                self.pixbuf = None
        self.queue_draw()

    def _on_draw(self, widget, cr):
        if self.pixbuf is None:
            return False
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        if width <= 0 or height <= 0:
            return False
        cache_size, scaled = self._cache
        if cache_size != (width, height):
            scale = max(width / self.pixbuf.get_width(), height / self.pixbuf.get_height())
            sw, sh = int(self.pixbuf.get_width() * scale), int(self.pixbuf.get_height() * scale)
            scaled = self.pixbuf.scale_simple(sw, sh, GdkPixbuf.InterpType.BILINEAR)
            self._cache = ((width, height), scaled)
        Gdk.cairo_set_source_pixbuf(cr, scaled, (width - scaled.get_width()) / 2,
                                    (height - scaled.get_height()) / 2)
        cr.paint()
        cr.set_source_rgba(0, 0, 0, 0.28)
        cr.paint()
        return False


def with_background(widget):
    overlay = Gtk.Overlay()
    background = ImageBackground()
    overlay.add(background)
    overlay.add_overlay(widget)
    overlay.set_overlay_pass_through(widget, False)
    return overlay, background


class CallWindow(Gtk.Window):
    def __init__(self, app, name, icon, incoming):
        super().__init__(title=f"Mintcord call — {name}")
        self.app, self.name, self.icon = app, name, icon
        self.incoming = incoming
        self.set_default_size(320, 220)
        self.set_position(Gtk.WindowPosition.CENTER)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(18)
        self.add(box)
        box.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG), True, True, 0)
        box.pack_start(Gtk.Label(label=f"{name} is {'calling you' if incoming else 'being called'}"), False, False, 0)
        self.state = Gtk.Label(label="Simulated call — no audio or network connection")
        box.pack_start(self.state, False, False, 0)
        buttons = Gtk.ButtonBox()
        self.end_button = Gtk.Button(label="End")
        self.end_button.connect("clicked", lambda _b: self.destroy())
        buttons.add(self.end_button)
        if incoming:
            answer = Gtk.Button(label="Answer")
            answer.connect("clicked", lambda _b: self.state.set_text("Simulated call connected"))
            buttons.add(answer)
            deny = Gtk.Button(label="Decline")
            deny.connect("clicked", lambda _b: self.destroy())
            buttons.add(deny)
        box.pack_start(buttons, False, False, 0)


class SettingsWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title="Mintcord Settings")
        self.app = app
        self.set_default_size(460, 420)
        self.set_transient_for(app)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(12)
        self.add(box)
        box.pack_start(Gtk.Label(label="Your status"), False, False, 0)
        status = Gtk.ComboBoxText()
        for name, _icon in STATUSES:
            status.append_text(name)
        status.set_active([x[0] for x in STATUSES].index(app.settings.data["status"]))
        status.connect("changed", lambda w: app.set_status(w.get_active_text()))
        box.pack_start(status, False, False, 0)
        box.pack_start(Gtk.Label(label="Status auto-reply text is stored locally."), False, False, 0)
        self.reply_entries = {}
        for name, _icon in STATUSES:
            row = Gtk.Box(spacing=6)
            row.pack_start(Gtk.Label(label=name, width_chars=10), False, False, 0)
            entry = Gtk.Entry()
            entry.set_text(app.settings.data["auto"].get(name, ""))
            entry.connect("changed", self.on_reply_changed, name)
            row.pack_start(entry, True, True, 0)
            box.pack_start(row, False, False, 0)
            self.reply_entries[name] = entry
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda _b: self.destroy())
        box.pack_end(close, False, False, 0)

    def on_reply_changed(self, entry, name):
        self.app.settings.data["auto"][name] = entry.get_text()
        self.app.settings.save()


class Mintcord(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)
        self.set_default_size(560, 520)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "assets", "mintcord.png")
        if os.path.isfile(icon_path):
            try:
                self.set_icon_from_file(icon_path)
            except GLib.Error:
                self.set_icon_name("user-info")
        else:
            self.set_icon_name("user-info")
        self.settings = Settings()
        self.settings_icon = theme_icon("unity-tweak-tool", "preferences-system")
        self.buffers = {}
        self.current = None
        self.call_win = None
        self.settings_win = None
        self.muted = False

        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.notebook = Gtk.Notebook()
        self.add(self.notebook)
        self.notebook.append_page(self._build_users_tab(), Gtk.Label(label="Users"))
        self.notebook.append_page(self._build_chat_tab(), Gtk.Label(label="Chat"))
        self.notebook.append_page(self._build_emoji_tab(), Gtk.Label(label="Emojis"))
        self.notebook.set_action_widget(self._build_top_right(), Gtk.PackType.END)
        self.refresh_backgrounds()

    def refresh_backgrounds(self):
        data = self.settings.data
        images, colors = data["images"], data["backgrounds"]
        name = self.current[0] if self.current else None
        rules = []
        main_path = usable_image(images.get(MAIN_KEY))
        self.main_bg.set_image(main_path)
        if main_path:
            rules.append("viewport.mainbg, list.mainbg, list.mainbg row { background-color: transparent; } "
                         "list.mainbg label { color: #ffffff; text-shadow: 0 1px 3px #000000; }")
        chat_path = usable_image(images.get(name)) if name else None
        if not chat_path and name not in colors:
            chat_path = usable_image(images.get(CHATS_KEY))
        self.chat_bg.set_image(chat_path)
        if chat_path:
            rules.append("textview.chatbg, textview.chatbg text { background-color: transparent; color: #ffffff; }")
        elif name in colors:
            color = colors[name]
            rules.append(f"textview.chatbg, textview.chatbg text "
                         f"{{ background-color: {color}; color: {text_color_for(color)}; }}")
        try:
            self.css.load_from_data(" ".join(rules or ["/* default */"]).encode())
        except GLib.Error:
            pass

    def notify(self, title, body, icon):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                     "org.freedesktop.Notifications", "Notify",
                     GLib.Variant("(susssasa{sv}i)",
                                  (APP_NAME, 0, icon, title, body, [], {}, 6000)),
                     None, Gio.DBusCallFlags.NONE, 1000, None, None, None)
        except (GLib.Error, TypeError):
            pass

    def _chat_is_visible(self, name):
        return (self.is_active() and self.notebook.get_current_page() == 1
                and self.current is not None and self.current[0] == name)

    def receive_message(self, name, icon, text):
        if name not in self.buffers:
            self.buffers[name] = Gtk.TextBuffer()
        buf = self.buffers[name]
        buf.insert(buf.get_end_iter(), f"{name}: {text}\n")
        status = self.settings.data["status"]
        if not self._chat_is_visible(name) and self.settings.data["notify"].get(status, True):
            self.notify(f"Message from {name}", text, icon)
        reply = self.settings.data["auto"].get(status, "").strip()
        if reply:
            buf.insert(buf.get_end_iter(), f"Auto-reply sent ({status}): {reply}\n")

    def _test_message(self, name, icon):
        GLib.timeout_add_seconds(TEST_MESSAGE_DELAY, self._deliver_test, name, icon)

    def _deliver_test(self, name, icon):
        self.receive_message(name, icon, random.choice(TEST_MESSAGES))
        return False

    def _build_top_right(self):
        box = Gtk.Box(spacing=4)
        self.status_image = Gtk.Image()
        box.pack_start(self.status_image, False, False, 6)
        send = Gtk.Button()
        send.set_image(Gtk.Image.new_from_icon_name(theme_icon("mail-attachment", "document-open"),
                                                    Gtk.IconSize.LARGE_TOOLBAR))
        send.set_relief(Gtk.ReliefStyle.NONE)
        send.set_tooltip_text("Send a file")
        send.connect("clicked", self._on_send_file)
        box.pack_start(send, False, False, 0)
        cfg = Gtk.Button()
        cfg.set_image(Gtk.Image.new_from_icon_name(self.settings_icon, Gtk.IconSize.LARGE_TOOLBAR))
        cfg.set_relief(Gtk.ReliefStyle.NONE)
        cfg.set_tooltip_text("Settings")
        cfg.connect("clicked", self._open_settings)
        box.pack_start(cfg, False, False, 0)
        self._update_status_image()
        box.show_all()
        return box

    def _update_status_image(self):
        status = self.settings.data["status"]
        self.status_image.set_from_icon_name(STATUS_ICON[status], Gtk.IconSize.LARGE_TOOLBAR)
        self.status_image.set_tooltip_text(f"Your status: {status}")

    def set_status(self, status):
        self.settings.data["status"] = status
        self.settings.save()
        self._update_status_image()

    def _open_settings(self, _button):
        if self.settings_win is not None:
            self.settings_win.present()
            return
        self.settings_win = SettingsWindow(self)
        self.settings_win.connect("destroy", lambda _w: setattr(self, "settings_win", None))
        self.settings_win.show_all()

    def _on_send_file(self, _button):
        if not self.current:
            dlg = Gtk.MessageDialog(transient_for=self, message_type=Gtk.MessageType.INFO,
                                    buttons=Gtk.ButtonsType.OK, text="Open a chat first")
            dlg.format_secondary_text("Double-click a user in the Users tab, then send a file.")
            dlg.run()
            dlg.destroy()
            return
        dlg = Gtk.FileChooserDialog(title="Send a file", transient_for=self,
                                    action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Send", Gtk.ResponseType.OK)
        if dlg.run() == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            try:
                size = human_size(os.path.getsize(path))
            except OSError:
                size = "?"
            buf = self.buffers[self.current[0]]
            buf.insert(buf.get_end_iter(),
                       f"You selected a file: {os.path.basename(path)} ({size}){self._queued_suffix()}\n")
            self.notebook.set_current_page(1)
        dlg.destroy()

    def _build_users_tab(self):
        listbox = Gtk.ListBox()
        listbox.set_activate_on_single_click(False)
        listbox.get_style_context().add_class("mainbg")
        for name, icon, status in TEST_USERS:
            listbox.add(self._make_row(name, icon, status))
        listbox.connect("row-activated", self._on_row_activated)
        scroll = Gtk.ScrolledWindow()
        scroll.add(listbox)
        scroll.get_child().get_style_context().add_class("mainbg")
        container, self.main_bg = with_background(scroll)
        return container

    def _make_row(self, name, icon, status):
        row = Gtk.ListBoxRow()
        row.user = (name, icon)
        events = Gtk.EventBox()
        events.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        box = Gtk.Box(spacing=10)
        box.set_border_width(6)
        box.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        name_label = Gtk.Label(xalign=0)
        name_label.set_markup(f"<b>{GLib.markup_escape_text(name)}</b>")
        status_label = Gtk.Label(label=status, xalign=0)
        status_label.get_style_context().add_class("dim-label")
        text_box.pack_start(name_label, False, False, 0)
        text_box.pack_start(status_label, False, False, 0)
        box.pack_start(text_box, True, True, 0)
        pov = Gtk.Button(label="POV")
        pov.set_relief(Gtk.ReliefStyle.NONE)
        pov.set_tooltip_text(f"See their side: {name} calls you")
        pov.connect("clicked", lambda _b: self._open_call(name, icon, incoming=True))
        box.pack_end(pov, False, False, 0)
        msg = Gtk.Button(label="Msg")
        msg.set_relief(Gtk.ReliefStyle.NONE)
        msg.set_tooltip_text(f"Test: {name} sends you a message in {TEST_MESSAGE_DELAY} seconds")
        msg.connect("clicked", lambda _b: self._test_message(name, icon))
        box.pack_end(msg, False, False, 0)
        call = Gtk.Button()
        call.set_image(Gtk.Image.new_from_icon_name("call-start", Gtk.IconSize.BUTTON))
        call.set_relief(Gtk.ReliefStyle.NONE)
        call.set_tooltip_text(f"Call {name}")
        call.set_opacity(0)
        call.connect("clicked", lambda _b: self._open_call(name, icon, incoming=False))
        events.connect("enter-notify-event", lambda _w, _e: call.set_opacity(1))
        events.connect("leave-notify-event", self._on_leave, call)
        events.add(box)
        row.add(events)
        return row

    @staticmethod
    def _on_leave(_widget, event, call_button):
        if event.detail != Gdk.NotifyType.INFERIOR:
            call_button.set_opacity(0)

    def _on_row_activated(self, _listbox, row):
        name, icon = row.user
        self._open_chat(name, icon)

    def _open_call(self, name, icon, incoming):
        if incoming:
            status = self.settings.data["status"]
            reply = self.settings.data["auto"].get(status, "").strip()
            if reply:
                self._open_chat(name, icon)
                buf = self.buffers[name]
                buf.insert(buf.get_end_iter(),
                           f"Missed call from {name} (you are {status}).\nAuto-reply sent: {reply}\n")
                return
        if self.call_win is not None:
            self.call_win.present()
            return
        self.call_win = CallWindow(self, name, icon, incoming)
        self.call_win.connect("destroy", lambda _w: setattr(self, "call_win", None))
        self.call_win.show_all()

    def _build_chat_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(6)
        header = Gtk.Box(spacing=6)
        self.peer_icon = Gtk.Image.new_from_icon_name("user-info", Gtk.IconSize.LARGE_TOOLBAR)
        self.peer_label = Gtk.Label(label="Pick a user in the Users tab (double-click)")
        header.pack_start(self.peer_icon, False, False, 0)
        header.pack_start(self.peer_label, False, False, 0)
        box.pack_start(header, False, False, 0)
        self.text_view = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD)
        self.text_view.get_style_context().add_class("chatbg")
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.text_view)
        container, self.chat_bg = with_background(scroll)
        box.pack_start(container, True, True, 0)
        row = Gtk.Box(spacing=6)
        self.entry = Gtk.Entry()
        self.entry.connect("activate", self._on_send)
        send = Gtk.Button(label="Send")
        send.connect("clicked", self._on_send)
        row.pack_start(self.entry, True, True, 0)
        row.pack_start(send, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    def _open_chat(self, name, icon):
        if name not in self.buffers:
            self.buffers[name] = Gtk.TextBuffer()
        self.current = (name, icon)
        self.text_view.set_buffer(self.buffers[name])
        self.peer_icon.set_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
        self.peer_label.set_text(name)
        self.emoji_status.set_text(f"Emojis will be sent to {name}")
        self.refresh_backgrounds()
        self.notebook.set_current_page(1)
        self.entry.grab_focus()

    def _queued_suffix(self):
        _name, icon = self.current
        return "  (queued - user is offline)" if icon in QUEUED_ICONS else ""

    def _on_send(self, _widget):
        message = self.entry.get_text().strip()
        if not message or not self.current:
            return
        buf = self.buffers[self.current[0]]
        buf.insert(buf.get_end_iter(), f"You: {message}{self._queued_suffix()}\n")
        self.entry.set_text("")

    def _build_emoji_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(6)
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(6)
        flow.set_homogeneous(True)
        for name in EMOJIS:
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            image = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.DND)
            image.set_pixel_size(40)
            button.add(image)
            button.set_tooltip_text(name.replace("face-", ""))
            button.connect("clicked", self._on_emoji, name)
            flow.add(button)
        scroll = Gtk.ScrolledWindow()
        scroll.add(flow)
        box.pack_start(scroll, True, True, 0)
        self.emoji_status = Gtk.Label(label="Open a chat first (double-click a user)")
        box.pack_start(self.emoji_status, False, False, 0)
        return box

    def _on_emoji(self, _button, name):
        if not self.current:
            self.emoji_status.set_text("Open a chat first (double-click a user)")
            return
        buf = self.buffers[self.current[0]]
        buf.insert(buf.get_end_iter(), "You: ")
        try:
            pixbuf = Gtk.IconTheme.get_default().load_icon(name, 28, 0)
            buf.insert_pixbuf(buf.get_end_iter(), pixbuf)
        except GLib.Error:
            buf.insert(buf.get_end_iter(), f":{name}:")
        buf.insert(buf.get_end_iter(), f"{self._queued_suffix()}\n")
        self.emoji_status.set_text(f"Sent {name.replace('face-', '')} to {self.current[0]}")
