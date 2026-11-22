#!/usr/bin/env python3
"""Mintcord prototype v0.5 - GUI shell with fake calls, mic mute, emojis,
file sending, notifications, photo/colour backgrounds and a settings window
(status, per-status actions, auto-replies).

Uses the system's stock icon theme names, so nothing is bundled and it
follows whatever icon theme Mint is using.

Settings are saved in ~/.config/mintcord/settings.json

Run:  python3 mintcord.py
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
ANSWER_DELAY = 10  # seconds the test users take to pick up
TEST_MESSAGE_DELAY = 5  # seconds before a test message arrives
CONFIG = os.path.join(GLib.get_user_config_dir(), "mintcord", "settings.json")
MAIN_KEY = "__main__"    # settings key: main menu photo
CHATS_KEY = "__chats__"  # settings key: photo for all chats

# (name, stock icon name, status label)
TEST_USERS = [
    ("Alice", "user-available", "Online"),
    ("Bob", "user-away", "Away"),
    ("Carol", "user-busy", "Busy"),
    ("Dave", "user-idle", "Idle"),
    ("Eve", "user-invisible", "Invisible"),
    ("Frank", "user-offline", "Offline"),
]
QUEUED_ICONS = {"user-offline", "user-invisible"}     # messages get queued
NO_ANSWER_ICONS = {"user-offline", "user-invisible"}  # never pick up calls
TEST_MESSAGES = [
    "Hey, you there?", "Want to hop on a call?", "Check this out!",
    "lol did you see that?", "Are you free later?",
]

# Your own status options: (label, stock icon)
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
    """First icon name that exists in the current theme (stock-icon fallback chain)."""
    theme = Gtk.IconTheme.get_default()
    for n in names:
        if theme.has_icon(n):
            return n
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
            with open(CONFIG) as f:
                saved = json.load(f)
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
            with open(CONFIG, "w") as f:
                json.dump(self.data, f, indent=2)
        except OSError:
            pass


class ImageBackground(Gtk.DrawingArea):
    """Paints a photo scaled to cover the area, with a dark layer so text stays readable."""

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
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        if w < 1 or h < 1:
            return False
        if self._cache[0] != (w, h):
            scale = max(w / self.pixbuf.get_width(), h / self.pixbuf.get_height())
            sw = max(1, int(self.pixbuf.get_width() * scale) + 1)
            sh = max(1, int(self.pixbuf.get_height() * scale) + 1)
            self._cache = ((w, h), self.pixbuf.scale_simple(sw, sh, GdkPixbuf.InterpType.BILINEAR))
        scaled = self._cache[1]
        cr.rectangle(0, 0, w, h)
        cr.clip()
        Gdk.cairo_set_source_pixbuf(cr, scaled,
                                    (w - scaled.get_width()) / 2, (h - scaled.get_height()) / 2)
        cr.paint()
        cr.set_source_rgba(0, 0, 0, 0.45)
        cr.paint()
        return False


def with_background(child):
    overlay = Gtk.Overlay()
    bg = ImageBackground()
    overlay.add(bg)
    overlay.add_overlay(child)
    return overlay, bg


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


class MicButton(Gtk.Button):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.set_relief(Gtk.ReliefStyle.NONE)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        overlay = Gtk.Overlay()
        img = Gtk.Image.new_from_icon_name("input-audio-microphone", Gtk.IconSize.DIALOG)
        img.set_pixel_size(64)
        overlay.add(img)
        self.slash = Gtk.DrawingArea()
        self.slash.connect("draw", self._draw_slash)
        overlay.add_overlay(self.slash)
        overlay.set_overlay_pass_through(self.slash, True)
        self.label = Gtk.Label()
        box.pack_start(overlay, False, False, 0)
        box.pack_start(self.label, False, False, 0)
        self.add(box)
        self.connect("clicked", self._toggle)
        self._refresh()

    def _toggle(self, _button):
        self.app.muted = not self.app.muted
        self._refresh()

    def _refresh(self):
        muted = self.app.muted
        self.label.set_text("Unmute" if muted else "Mute")
        self.set_tooltip_text("Unmute microphone" if muted else "Mute microphone")
        self.slash.queue_draw()

    def _draw_slash(self, area, cr):
        if not self.app.muted:
            return False
        w, h = area.get_allocated_width(), area.get_allocated_height()
        cr.set_line_cap(1)
        for rgba, width in (((1, 1, 1, 0.9), 11), ((0.9, 0.1, 0.1, 1), 7)):
            cr.set_source_rgba(*rgba)
            cr.set_line_width(width)
            cr.move_to(w * 0.18, h * 0.85)
            cr.line_to(w * 0.82, h * 0.15)
            cr.stroke()
        return False


class CallWindow(Gtk.Window):
    def __init__(self, app, name, icon, incoming):
        super().__init__(title=f"Call - {name}")
        self.app = app
        self.set_transient_for(app)
        self.set_default_size(420, 380)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.icon = icon
        self.seconds = 0
        self.sources = set()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(20)
        self.add(box)
        who = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        who.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
        title = Gtk.Label()
        title.set_markup(f"<big><b>{GLib.markup_escape_text(name)}</b></big>")
        who.pack_start(title, False, False, 0)
        box.pack_start(who, False, False, 0)
        self.status = Gtk.Label()
        box.pack_start(self.status, False, False, 0)
        self.btn_box = Gtk.Box(spacing=30, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        box.pack_start(self.btn_box, True, True, 0)
        if incoming:
            self.status.set_text("Incoming call...")
            self._show_incoming()
        else:
            self.status.set_text("Calling...")
            self._show_stop()
            self._after(ANSWER_DELAY, self._npc_answers)
        self.connect("destroy", self._cleanup)

    def _clear_buttons(self):
        for child in self.btn_box.get_children():
            self.btn_box.remove(child)

    def _show_stop(self):
        self._clear_buttons()
        mic = MicButton(self.app)
        mic.set_valign(Gtk.Align.CENTER)
        stop = big_button("call-stop", "End call", 128)
        stop.set_valign(Gtk.Align.CENTER)
        stop.connect("clicked", lambda _b: self.destroy())
        self.btn_box.pack_start(mic, False, False, 0)
        self.btn_box.pack_start(stop, False, False, 0)
        self.btn_box.show_all()

    def _show_incoming(self):
        self._clear_buttons()
        accept = big_button("call-start", "Accept")
        accept.connect("clicked", lambda _b: self._connected())
        deny = big_button("call-stop", "Deny")
        deny.connect("clicked", lambda _b: self.destroy())
        self.btn_box.pack_start(accept, False, False, 0)
        self.btn_box.pack_start(deny, False, False, 0)
        self.btn_box.show_all()

    def _npc_answers(self):
        if self.icon in NO_ANSWER_ICONS:
            self.status.set_text("No answer")
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
        m, s = divmod(self.seconds, 60)
        self.status.set_text(f"Connected  {m:02d}:{s:02d}")

    def _after(self, seconds, fn):
        holder = []
        def run():
            self.sources.discard(holder[0])
            fn()
            return False
        holder.append(GLib.timeout_add_seconds(seconds, run))
        self.sources.add(holder[0])

    def _cleanup(self, _widget):
        for sid in self.sources:
            GLib.source_remove(sid)
        self.sources.clear()


class SettingsWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title=f"{APP_NAME} - Settings")
        self.app = app
        self.set_transient_for(app)
        self.set_default_size(560, 700)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_icon_name(app.settings_icon)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_border_width(10)
        self.add(outer)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_border_width(6)
        scroll = Gtk.ScrolledWindow()
        scroll.add(content)
        outer.pack_start(scroll, True, True, 0)
        content.pack_start(self._header("My status"), False, False, 0)
        store = Gtk.ListStore(str, str)
        for label, icon in STATUSES:
            store.append([icon, label])
        combo = Gtk.ComboBox.new_with_model(store)
        pix = Gtk.CellRendererPixbuf()
        combo.pack_start(pix, False)
        combo.add_attribute(pix, "icon-name", 0)
        txt = Gtk.CellRendererText()
        combo.pack_start(txt, True)
        combo.add_attribute(txt, "text", 1)
        combo.set_active([s[0] for s in STATUSES].index(app.settings.data["status"]))
        combo.connect("changed", lambda c: app.set_status(STATUSES[c.get_active()][0]))
        content.pack_start(combo, False, False, 0)
        content.pack_start(self._header("Actions for each status"), False, False, 0)
        hint = Gtk.Label(label="What happens when someone messages or calls you while you are on that status. Leave the reply empty to turn it off.", xalign=0)
        hint.set_line_wrap(True)
        hint.get_style_context().add_class("dim-label")
        content.pack_start(hint, False, False, 0)
        grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        grid.attach(Gtk.Label(label="Notifications"), 2, 0, 1, 1)
        grid.attach(Gtk.Label(label="Automatic reply", xalign=0), 3, 0, 1, 1)
        for i, (label, icon) in enumerate(STATUSES, start=1):
            grid.attach(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON), 0, i, 1, 1)
            grid.attach(Gtk.Label(label=label, xalign=0), 1, i, 1, 1)
            notify = Gtk.CheckButton(halign=Gtk.Align.CENTER)
            notify.set_active(app.settings.data["notify"].get(label, True))
            notify.connect("toggled", self._on_notify_toggled, label)
            grid.attach(notify, 2, i, 1, 1)
            entry = Gtk.Entry(hexpand=True)
            entry.set_text(app.settings.data["auto"].get(label, ""))
            entry.set_placeholder_text("No automatic reply")
            entry.connect("changed", self._on_auto_changed, label)
            grid.attach(entry, 3, i, 1, 1)
        content.pack_start(grid, False, False, 0)
        content.pack_start(self._header("Backgrounds"), False, False, 0)
        bg = Gtk.Grid(column_spacing=10, row_spacing=6)
        self._add_bg_row(bg, 0, MAIN_KEY, "go-home", "Main menu", False)
        self._add_bg_row(bg, 1, CHATS_KEY, "user-info", "All chats", False)
        for i, (name, icon, _status) in enumerate(TEST_USERS, start=2):
            self._add_bg_row(bg, i, name, icon, name, True)
        content.pack_start(bg, False, False, 0)
        note = Gtk.Label(label='A photo or colour set for one chat wins over the "All chats" photo.', xalign=0)
        note.set_line_wrap(True)
        note.get_style_context().add_class("dim-label")
        content.pack_start(note, False, False, 0)
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda _b: self.destroy())
        outer.pack_start(close, False, False, 0)

    @staticmethod
    def _header(text):
        label = Gtk.Label(xalign=0)
        label.set_markup(f"<b>{GLib.markup_escape_text(text)}</b>")
        return label

    def _on_notify_toggled(self, button, status):
        self.app.settings.data["notify"][status] = button.get_active()
        self.app.settings.save()

    def _on_auto_changed(self, entry, status):
        self.app.settings.data["auto"][status] = entry.get_text()
        self.app.settings.save()

    def _choose_image(self):
        dlg = Gtk.FileChooserDialog(title="Choose a photo", transient_for=self, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Choose", Gtk.ResponseType.OK)
        flt = Gtk.FileFilter()
        flt.set_name("Images")
        flt.add_pixbuf_formats()
        dlg.add_filter(flt)
        path = dlg.get_filename() if dlg.run() == Gtk.ResponseType.OK else None
        dlg.destroy()
        return path

    def _add_bg_row(self, grid, row, key, icon, label, with_color):
        data = self.app.settings.data
        images, colors = data["images"], data["backgrounds"]
        grid.attach(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON), 0, row, 1, 1)
        grid.attach(Gtk.Label(label=label, xalign=0, hexpand=True), 1, row, 1, 1)
        picker = None
        if with_color:
            rgba = Gdk.RGBA()
            rgba.parse(colors.get(key) or "#ffffff")
            picker = Gtk.ColorButton.new_with_rgba(rgba)
            grid.attach(picker, 2, row, 1, 1)
        photo = Gtk.Button(label=os.path.basename(images[key]) if key in images else "Choose photo...")
        photo.get_child().set_max_width_chars(16)
        photo.get_child().set_ellipsize(Pango.EllipsizeMode.END)
        reset = Gtk.Button(label="Reset")
        reset.set_sensitive(key in images or key in colors)
        grid.attach(photo, 3, row, 1, 1)
        grid.attach(reset, 4, row, 1, 1)

        def changed():
            self.app.settings.save()
            reset.set_sensitive(key in images or key in colors)
            self.app.refresh_backgrounds()
        def on_color(_b):
            colors[key] = to_hex(picker.get_rgba())
            changed()
        def on_photo(_b):
            path = self._choose_image()
            if path:
                images[key] = path
                photo.set_label(os.path.basename(path))
                changed()
        def on_reset(_b):
            images.pop(key, None)
            colors.pop(key, None)
            photo.set_label("Choose photo...")
            if picker is not None:
                white = Gdk.RGBA()
                white.parse("#ffffff")
                picker.set_rgba(white)
            changed()
        if picker is not None:
            picker.connect("color-set", on_color)
        photo.connect("clicked", on_photo)
        reset.connect("clicked", on_reset)


class Mintcord(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)
        self.set_default_size(560, 520)
        self.set_icon_name("user-info")
        self.settings = Settings()
        self.settings_icon = theme_icon("unity-tweak-tool", "preferences-system")
        self.buffers = {}
        self.current = None
        self.call_win = None
        self.settings_win = None
        self.muted = False

        # Use the same project icon when running from source or after installation.
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "mintcord.svg"))
        if not os.path.isfile(icon_path):
            icon_path = "/opt/mintcord/assets/mintcord.svg"
        if os.path.isfile(icon_path):
            try:
                self.set_icon_from_file(icon_path)
            except GLib.Error:
                pass

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
            rules.append("viewport.mainbg, list.mainbg, list.mainbg row { background-color: transparent; } list.mainbg label { color: #ffffff; text-shadow: 0 1px 3px #000000; }")
        chat_path = usable_image(images.get(name)) if name else None
        if not chat_path and name not in colors:
            chat_path = usable_image(images.get(CHATS_KEY))
        self.chat_bg.set_image(chat_path)
        if chat_path:
            rules.append("textview.chatbg, textview.chatbg text { background-color: transparent; color: #ffffff; }")
        elif name in colors:
            color = colors[name]
            rules.append(f"textview.chatbg, textview.chatbg text {{ background-color: {color}; color: {text_color_for(color)}; }}")
        try:
            self.css.load_from_data(" ".join(rules or ["/* default */"]).encode())
        except GLib.Error:
            pass

    def notify(self, title, body, icon):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                     "org.freedesktop.Notifications", "Notify",
                     GLib.Variant("(susssasa{sv}i)", (APP_NAME, 0, icon, title, body, [], {}, 6000)),
                     None, Gio.DBusCallFlags.NONE, 1000, None, None, None)
        except (GLib.Error, TypeError):
            pass

    def _chat_is_visible(self, name):
        return self.is_active() and self.notebook.get_current_page() == 1 and self.current is not None and self.current[0] == name

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
        send.set_image(Gtk.Image.new_from_icon_name(theme_icon("mail-attachment", "document-open"), Gtk.IconSize.LARGE_TOOLBAR))
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
            dlg = Gtk.MessageDialog(transient_for=self, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text="Open a chat first")
            dlg.format_secondary_text("Double-click a user in the Users tab, then send a file.")
            dlg.run()
            dlg.destroy()
            return
        dlg = Gtk.FileChooserDialog(title="Send a file", transient_for=self, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Send", Gtk.ResponseType.OK)
        if dlg.run() == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            try:
                size = human_size(os.path.getsize(path))
            except OSError:
                size = "?"
            buf = self.buffers[self.current[0]]
            buf.insert(buf.get_end_iter(), f"You sent a file: {os.path.basename(path)} ({size}){self._queued_suffix()}\n")
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
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        n = Gtk.Label(xalign=0)
        n.set_markup(f"<b>{GLib.markup_escape_text(name)}</b>")
        s = Gtk.Label(label=status, xalign=0)
        s.get_style_context().add_class("dim-label")
        text.pack_start(n, False, False, 0)
        text.pack_start(s, False, False, 0)
        box.pack_start(text, True, True, 0)
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
        box.pack_end(call, False, False, 0)
        events.connect("enter-notify-event", lambda _w, _e: call.set_opacity(1))
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
        if incoming:
            status = self.settings.data["status"]
            reply = self.settings.data["auto"].get(status, "").strip()
            if reply:
                self._open_chat(name, icon)
                buf = self.buffers[name]
                buf.insert(buf.get_end_iter(), f"Missed call from {name} (you are {status}).\nAuto-reply sent: {reply}\n")
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
        self.current = (name, icon)
        if name not in self.buffers:
            self.buffers[name] = Gtk.TextBuffer()
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
        text = self.entry.get_text().strip()
        if not text or not self.current:
            return
        buf = self.buffers[self.current[0]]
        buf.insert(buf.get_end_iter(), f"You: {text}{self._queued_suffix()}\n")
        self.entry.set_text("")

    def _build_emoji_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(6)
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(6)
        flow.set_homogeneous(True)
        for name in EMOJIS:
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            img = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.DND)
            img.set_pixel_size(40)
            btn.add(img)
            btn.set_tooltip_text(name.replace("face-", ""))
            btn.connect("clicked", self._on_emoji, name)
            flow.add(btn)
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


if __name__ == "__main__":
    win = Mintcord()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
