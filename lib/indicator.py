import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")

from gi.repository import AyatanaAppIndicator3 as AppIndicator, Gio, GLib, Gtk

import threading
import os

from .api import APIClient, APIAuthError, APIError
from .config import fmt_count, fmt_reset, load_config, save_config
from .detail import DetailWindow
from .settings import SettingsWindow

APP_ID = "com.minimax.usage-widget"
INDICATOR_ID = "minimax-usage-indicator"


class MiniMaxApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._config = load_config()
        self._client = None
        self._data = None
        self._indicator = None
        self._win = None
        self._timer_id = None

    def do_activate(self):
        self.hold()

        icon = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "blank-icon.svg",
        )
        self._indicator = AppIndicator.Indicator.new(
            INDICATOR_ID,
            icon,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_label("MM --", "")
        self._indicator.set_title("MiniMax Quota")
        self._build_menu()
        self._indicator.set_menu(self._menu)

        if self._config.get("api_key"):
            self._client = APIClient(self._config["api_key"])
            self._refresh()
            self._schedule_refresh()
        else:
            self._indicator.set_label("MM ?", "")
            self._set_status("No API key configured")

    # ── Menu ───────────────────────────────────────────────

    def _build_menu(self):
        self._menu = Gtk.Menu()
        self._mi = {}

        self._mi["header"] = Gtk.MenuItem(label="MiniMax Token Plan")
        self._mi["header"].set_sensitive(False)
        self._menu.append(self._mi["header"])
        self._menu.append(Gtk.SeparatorMenuItem())

        # Interval Quota
        mi = Gtk.MenuItem(label="Interval Quota (5h Window)")
        mi.set_sensitive(False)
        self._menu.append(mi)

        self._mi["int_details"] = Gtk.MenuItem(label="  Remaining: -- / -- requests")
        self._mi["int_details"].set_sensitive(False)
        self._menu.append(self._mi["int_details"])

        self._mi["int_reset"] = Gtk.MenuItem(label="  \u21bb Resets in: --")
        self._mi["int_reset"].set_sensitive(False)
        self._menu.append(self._mi["int_reset"])

        self._menu.append(Gtk.SeparatorMenuItem())

        # Weekly Quota
        mi = Gtk.MenuItem(label="Weekly Quota")
        mi.set_sensitive(False)
        self._menu.append(mi)

        self._mi["wk_details"] = Gtk.MenuItem(label="  Remaining: -- / -- requests/tokens")
        self._mi["wk_details"].set_sensitive(False)
        self._menu.append(self._mi["wk_details"])

        self._mi["wk_reset"] = Gtk.MenuItem(label="  \u21bb Resets in: --")
        self._mi["wk_reset"].set_sensitive(False)
        self._menu.append(self._mi["wk_reset"])

        self._menu.append(Gtk.SeparatorMenuItem())

        # Plan Info
        self._mi["model_name"] = Gtk.MenuItem(label="Plan Model: --")
        self._mi["model_name"].set_sensitive(False)
        self._menu.append(self._mi["model_name"])

        self._menu.append(Gtk.SeparatorMenuItem())

        mi = Gtk.MenuItem(label="Open Details Window")
        mi.connect("activate", self._on_detail)
        self._menu.append(mi)

        mi = Gtk.MenuItem(label="Refresh Now")
        mi.connect("activate", lambda _: self._refresh())
        self._menu.append(mi)

        mi = Gtk.MenuItem(label="Settings\u2026")
        mi.connect("activate", self._on_settings)
        self._menu.append(mi)

        self._menu.append(Gtk.SeparatorMenuItem())

        self._mi["status"] = Gtk.MenuItem(label="")
        self._mi["status"].set_sensitive(False)
        self._menu.append(self._mi["status"])

        mi = Gtk.MenuItem(label="Quit")
        mi.connect("activate", self._on_quit)
        self._menu.append(mi)

        self._menu.show_all()

    def _update_menu(self, d):
        M = self._mi
        M["header"].set_label(f"MiniMax Token Plan ({d['model_name']})")
        
        M["int_details"].set_label(
            f"  Used: {fmt_count(d['interval_used'])} / "
            f"{fmt_count(d['interval_total'])} requests ({d['interval_pct']}%)"
        )
        M["int_reset"].set_label(f"  \u21bb Resets in: {fmt_reset(d['interval_reset_ms'])}")

        if d["weekly_total"] > 0:
            M["wk_details"].set_label(
                f"  Used: {fmt_count(d['weekly_used'])} / "
                f"{fmt_count(d['weekly_total'])} requests/tokens ({d['weekly_pct']}%)"
            )
            M["wk_reset"].set_label(f"  \u21bb Resets in: {fmt_reset(d['weekly_reset_ms'])}")
            M["wk_details"].show()
            M["wk_reset"].show()
        else:
            M["wk_details"].set_label("  Used: Unlimited Weekly")
            M["wk_reset"].hide()

        M["model_name"].set_label(f"Plan Model: {d['model_name']}")
        M["status"].set_label(f"Updated {d['ts'].strftime('%H:%M:%S')}")

    def _set_status(self, msg):
        self._mi["status"].set_label(msg)

    # ── Data fetching ──────────────────────────────────────

    def _refresh(self):
        if not self._client:
            return
        self._set_status("Refreshing\u2026")
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self):
        try:
            data = self._client.fetch_all()
            GLib.idle_add(self._on_data, data)
        except APIAuthError as e:
            GLib.idle_add(self._on_error, str(e))
        except APIError as e:
            GLib.idle_add(self._on_error, str(e))

    def _on_data(self, data):
        self._data = data
        self._indicator.set_label(f"MM {data['interval_pct']}%", "")
        self._update_menu(data)
        if self._win:
            self._win.update_data(data)
        return False

    def _on_error(self, msg):
        self._indicator.set_label("MM ERR", "")
        self._set_status(f"Error: {msg}")
        return False

    def _schedule_refresh(self):
        if self._timer_id:
            GLib.source_remove(self._timer_id)
        secs = self._config.get("refresh_interval", 300)
        self._timer_id = GLib.timeout_add_seconds(secs, self._auto_refresh)

    def _auto_refresh(self):
        self._refresh()
        return GLib.SOURCE_CONTINUE

    # ── Windows ────────────────────────────────────────────

    def _on_detail(self, _):
        if self._win:
            self._win.present()
            return
        self._win = DetailWindow(self)
        self._win.connect("destroy", self._on_win_close)
        if self._data:
            self._win.update_data(self._data)
        self._win.show_all()

    def _on_win_close(self, win):
        self._win = None

    def _on_settings(self, _):
        def on_save(cfg):
            self._config = cfg
            save_config(self._config)
            if self._config["api_key"]:
                self._client = APIClient(self._config["api_key"])
                self._refresh()
                self._schedule_refresh()
            else:
                self._client = None
                self._indicator.set_label("MM ?", "")
                self._set_status("No API key configured")

        win = SettingsWindow(self, on_save)
        win.show_all()

    def _on_quit(self, _):
        if self._timer_id:
            GLib.source_remove(self._timer_id)
        self.quit()


def main():
    GLib.set_prgname(APP_ID)
    GLib.set_application_name("MiniMax Quota Indicator")

    # Set default window icon from file so all windows inherit it
    icon_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "minimax-usage-indicator.svg",
    )
    try:
        from gi.repository import GdkPixbuf

        Gtk.Window.set_default_icon(
            GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 128, 128)
        )
    except Exception:
        Gtk.Window.set_default_icon_name(APP_ID)

    app = MiniMaxApp()
    app.run()

