#!/usr/bin/env python3
"""Mintcord graphical installer for Linux Mint / Ubuntu-based desktops."""
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf

REQUIRED = ["python3", "python3-gi", "gir1.2-gtk-3.0"]


class Installer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Mintcord Installer")
        self.set_border_width(18)
        self.set_default_size(480, 410)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.source = Path(__file__).resolve().parent.parent
        self.process = None
        self.steps = []
        self.step_index = 0
        self.uninstalling = False

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(outer)
        icon_path = self.source / "assets" / "mintcord.png"
        if icon_path.is_file():
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon_path), 112, 112, True)
                self.set_icon(pix)
                image = Gtk.Image.new_from_pixbuf(pix)
                image.set_halign(Gtk.Align.CENTER)
                outer.pack_start(image, False, False, 0)
            except Exception as exc:
                print(f"Could not load Mintcord icon: {exc}")

        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Mintcord</span>")
        outer.pack_start(title, False, False, 0)
        subtitle = Gtk.Label(label="Install or remove Mintcord on this computer")
        subtitle.get_style_context().add_class("dim-label")
        outer.pack_start(subtitle, False, False, 0)

        self.status = Gtk.Label(label="Ready. The installer will check dependencies first.")
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

        self.log = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.log.set_size_request(-1, 90)
        self.log.get_buffer().set_text(
            "Application files: /opt/mintcord\n"
            "Personal settings and data are kept in your home folder."
        )
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
            message = ("Mintcord was removed. Your personal data was preserved."
                       if self.uninstalling else "Mintcord installation completed.")
            self.status.set_text(message)
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
            # Keep command output so errors are visible in the installer log.
            self.process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
        except Exception as exc:
            self.fail(str(exc))
            return False
        GLib.timeout_add(250, self.poll_process)
        return False

    def poll_process(self):
        if self.process is None:
            return False
        code = self.process.poll()
        if code is None:
            return True
        output, _ = self.process.communicate()
        if output:
            for line in output.splitlines()[-12:]:
                self.write_log(line)
        if code != 0:
            self.fail(f"Command failed (exit code {code}). See the log above.")
            return False
        self.step_index += 1
        self.progress.set_fraction(self.step_index / max(1, len(self.steps)))
        GLib.idle_add(self.run_next)
        return False

    def fail(self, message):
        self.spinner.stop()
        self.status.set_text("Operation failed.")
        self.progress.set_text("Failed")
        self.write_log(message)
        self.install_button.set_sensitive(True)
        self.uninstall_button.set_sensitive(Path("/opt/mintcord").exists())
        self.close_button.set_sensitive(True)

    def start_install(self, _button):
        if not (self.source / "app" / "main.py").is_file():
            self.fail("Run the installer from the extracted Mintcord project folder.")
            return
        missing = []
        for package in REQUIRED:
            check = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", package],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
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
            buttons=Gtk.ButtonsType.CANCEL, text="Uninstall Mintcord?"
        )
        dialog.format_secondary_text(
            "The application will be removed. Your settings and local data in your home folder will be kept."
        )
        dialog.add_button("Uninstall", Gtk.ResponseType.ACCEPT)
        answer = dialog.run()
        dialog.destroy()
        if answer == Gtk.ResponseType.ACCEPT:
            self.run_steps(
                [("Removing Mintcord application files…", ["pkexec", "bash", str(helper)])],
                uninstall=True
            )


if __name__ == "__main__":
    win = Installer()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
