#!/usr/bin/env python3
"""Mintcord graphical installer for Linux Mint / Ubuntu-based desktops."""
import subprocess
import tempfile
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf

REQUIRED = ["python3", "python3-gi", "gir1.2-gtk-3.0"]


class Installer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Mintcord Installer")
        self.set_border_width(18)
        self.set_default_size(500, 420)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.source = Path(__file__).resolve().parent.parent
        self.process = None
        self.process_log = None
        self.process_log_path = None
        self.steps = []
        self.step_index = 0
        self.uninstalling = False

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(outer)
        icon_path = self.source / "assets" / "mintcord.svg"
        if icon_path.exists():
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon_path), 112, 112, True)
                image = Gtk.Image.new_from_pixbuf(pix)
                image.set_halign(Gtk.Align.CENTER)
                outer.pack_start(image, False, False, 0)
            except GLib.Error:
                pass

        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Mintcord</span>")
        outer.pack_start(title, False, False, 0)
        subtitle = Gtk.Label(label="Install or remove Mintcord on this computer")
        subtitle.get_style_context().add_class("dim-label")
        outer.pack_start(subtitle, False, False, 0)

        self.status = Gtk.Label(label="Ready. Select Install Mintcord to begin.")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        outer.pack_start(self.status, False, False, 4)

        self.spinner = Gtk.Spinner()
        self.spinner.set_halign(Gtk.Align.CENTER)
        outer.pack_start(self.spinner, False, False, 2)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_text("Waiting")
        outer.pack_start(self.progress, False, False, 0)

        self.log = Gtk.TextView(editable=False, cursor_visible=False,
                                wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.log.set_size_request(-1, 100)
        self.log.get_buffer().set_text(
            "Application files: /opt/mintcord\n"
            "Personal settings and data are kept in your home folder.")
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.log)
        outer.pack_start(scroll, True, True, 0)

        buttons = Gtk.ButtonBox()
        buttons.set_layout(Gtk.ButtonBoxStyle.END)
        buttons.set_spacing(8)
        self.close_button = Gtk.Button(label="Close")
        self.close_button.connect("clicked", lambda _b: self.destroy())
        self.uninstall_button = Gtk.Button(label="Uninstall")
        self.uninstall_button.connect("clicked", self.start_uninstall)
        self.install_button = Gtk.Button(label="Install Mintcord")
        self.install_button.get_style_context().add_class("suggested-action")
        self.install_button.connect("clicked", self.start_install)
        buttons.add(self.close_button)
        buttons.add(self.uninstall_button)
        buttons.add(self.install_button)
        outer.pack_start(buttons, False, False, 0)

        self.uninstall_button.set_sensitive(Path("/opt/mintcord").exists())
        self.show_all()

    def write_log(self, line):
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), line + "\n")
        mark = buf.create_mark(None, buf.get_end_iter(), False)
        self.log.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def set_busy(self, text):
        self.status.set_text(text)
        self.spinner.start()
        self.install_button.set_sensitive(False)
        self.uninstall_button.set_sensitive(False)
        self.close_button.set_sensitive(False)

    def run_steps(self, steps, uninstall=False):
        self.steps = steps
        self.step_index = 0
        self.uninstalling = uninstall
        self.progress.set_fraction(0)
        self.progress.set_text("Starting")
        self.set_busy("Working… please keep this window open.")
        self.run_next()

    def run_next(self):
        if self.step_index >= len(self.steps):
            self.spinner.stop()
            self.progress.set_fraction(1)
            self.progress.set_text("Complete")
            self.status.set_text(
                "Mintcord was removed. Your personal data was preserved."
                if self.uninstalling else "Mintcord installation completed.")
            self.write_log("Finished successfully.")
            self.install_button.set_sensitive(True)
            self.uninstall_button.set_sensitive(Path("/opt/mintcord").exists())
            self.close_button.set_sensitive(True)
            return False

        label, command = self.steps[self.step_index]
        self.status.set_text(label)
        self.progress.set_text(f"Step {self.step_index + 1} of {len(self.steps)}")
        self.write_log(label)
        try:
            self.process_log = tempfile.NamedTemporaryFile(
                mode="w+", prefix="mintcord-installer-", suffix=".log", delete=False)
            self.process_log_path = self.process_log.name
            self.process = subprocess.Popen(
                command, stdout=self.process_log, stderr=subprocess.STDOUT)
        except Exception as exc:
            self.fail(f"Could not start command: {exc}")
            return False
        GLib.timeout_add(250, self.poll_process)
        return False

    def poll_process(self):
        if self.process is None:
            return False
        code = self.process.poll()
        if code is None:
            return True

        if self.process_log:
            self.process_log.flush()
            self.process_log.close()
            self.process_log = None

        if code != 0:
            details = ""
            try:
                details = Path(self.process_log_path).read_text(errors="replace")[-1800:]
            except (OSError, TypeError):
                pass
            self.fail(f"Command exited with code {code}.\n{details.strip() or 'No error output was returned. Check whether the administrator prompt was cancelled.'}")
            return False

        self.step_index += 1
        self.progress.set_fraction(self.step_index / max(1, len(self.steps)))
        GLib.idle_add(self.run_next)
        return False

    def fail(self, message):
        self.spinner.stop()
        self.status.set_text("Operation failed. See details below.")
        self.progress.set_text("Failed")
        self.write_log(message)
        self.install_button.set_sensitive(True)
        self.uninstall_button.set_sensitive(Path("/opt/mintcord").exists())
        self.close_button.set_sensitive(True)
        if self.process_log:
            self.process_log.close()
            self.process_log = None

    def start_install(self, _button):
        if not (self.source / "app" / "main.py").is_file():
            self.fail("Run install.sh from the extracted Mintcord project folder.")
            return
        if not (self.source / "assets" / "mintcord.svg").is_file():
            self.fail("The Mintcord logo is missing from assets/mintcord.svg.")
            return
        if not shutil_which("pkexec"):
            self.fail("pkexec is missing. Install the Linux PolicyKit authentication helper, then retry.")
            return

        missing = []
        for package in REQUIRED:
            check = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", package],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if "install ok installed" not in check.stdout:
                missing.append(package)

        steps = []
        if missing:
            steps.append(("Refreshing package lists (administrator permission required)…",
                          ["pkexec", "apt-get", "update"]))
            steps.append(("Installing missing system dependencies…",
                          ["pkexec", "apt-get", "install", "-y"] + missing))
        steps.append(("Installing Mintcord and creating its application-menu shortcut…",
                      ["pkexec", "bash", str(self.source / "installer" / "install_system.sh"),
                       str(self.source)]))
        self.run_steps(steps)

    def start_uninstall(self, _button):
        helper = Path("/opt/mintcord/installer/uninstall_system.sh")
        if not helper.is_file():
            self.fail("The installed uninstaller was not found. Reinstall Mintcord first.")
            return
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.CANCEL, text="Uninstall Mintcord?")
        dialog.format_secondary_text(
            "The application will be removed. Your settings and local data in your home folder will be kept.")
        dialog.add_button("Uninstall", Gtk.ResponseType.ACCEPT)
        answer = dialog.run()
        dialog.destroy()
        if answer == Gtk.ResponseType.ACCEPT:
            self.run_steps(
                [("Removing Mintcord application files…",
                  ["pkexec", "bash", str(helper)])], uninstall=True)


def shutil_which(command):
    from shutil import which
    return which(command)


if __name__ == "__main__":
    win = Installer()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
