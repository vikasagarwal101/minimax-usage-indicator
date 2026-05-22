import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

from .config import load_config


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app, on_save):
        super().__init__(title="MiniMax Quota Settings", application=app)
        self.on_save_cb = on_save
        self.set_default_size(400, -1)
        self.set_border_width(0)

        self._build()

    def _build(self):
        header = Gtk.HeaderBar(title="MiniMax Quota Settings", show_close_button=True)
        save_btn = Gtk.Button(label="Save")
        save_btn.get_style_context().add_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        header.pack_end(save_btn)
        self.set_titlebar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)

        content.add(Gtk.Label(label="Token Plan Key", xalign=0))

        self.key_entry = Gtk.Entry()
        self.key_entry.set_visibility(False)
        self.key_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.key_entry.set_placeholder_text("Paste your MiniMax Token Plan Key (sk-cp-...)")
        config = load_config()
        self.key_entry.set_text(config.get("api_key", ""))
        self.key_entry.set_hexpand(True)
        content.add(self.key_entry)

        show_btn = Gtk.CheckButton.new_with_label("Show key")
        show_btn.connect(
            "toggled", lambda b: self.key_entry.set_visibility(b.get_active())
        )
        content.add(show_btn)

        content.add(Gtk.Label(label="Refresh Interval (minutes)", xalign=0))

        adj = Gtk.Adjustment(
            value=config.get("refresh_interval", 300) / 60,
            lower=1, upper=60, step_increment=1, page_increment=5,
        )
        self.refresh_spin = Gtk.SpinButton(adjustment=adj)
        content.add(self.refresh_spin)

        self.add(content)

    def _on_save(self, _):
        cfg = {}
        cfg["api_key"] = self.key_entry.get_text().strip()
        cfg["refresh_interval"] = int(self.refresh_spin.get_value() * 60)
        self.on_save_cb(cfg)
        self.destroy()

