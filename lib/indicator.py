import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")

from gi.repository import AyatanaAppIndicator3 as AppIndicator, Gio, GLib, Gtk

import threading
import queue
import os
import argparse
import json

from .api import APIClient, APIAuthError, APIError
from .config import fmt_count, fmt_reset, load_config, save_config
from .detail import DetailWindow
from .settings import SettingsWindow

APP_ID = "com.minimax.usage-widget"
INDICATOR_ID = "minimax-usage-indicator"
CONSOLE_URL = "https://platform.minimax.io/subscribe/token-plan"


class MiniMaxApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._config = load_config()
        self._client = None
        self._data = None
        self._indicator = None
        self._win = None
        self._timer_id = None
        self._fetch_thread = None
        self._fetch_queue = queue.Queue()
        self._fetch_shutdown = False
        self._last_error = ""
        self._last_threshold_notice = ""

    def do_activate(self):
        self.hold()

        icon = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "minimax-usage-indicator.svg",
        )
        self._indicator = AppIndicator.Indicator.new(
            INDICATOR_ID,
            icon,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_label("MMX --", "")
        self._indicator.set_title("MiniMax Quota")
        self._build_menu()
        self._indicator.set_menu(self._menu)

        if self._config.get("api_key"):
            self._client = APIClient(self._config["api_key"])
            self._start_fetch_worker()
            self._refresh()
            self._schedule_refresh()
        else:
            self._indicator.set_label("MMX ?", "")
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

        self._mi["wk_details"] = Gtk.MenuItem(
            label="  Remaining: -- / -- requests/tokens"
        )
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

        mi = Gtk.MenuItem(label="Open MiniMax Console")
        mi.connect("activate", self._on_open_console)
        self._menu.append(mi)

        mi = Gtk.MenuItem(label="Settings...")
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
        # model_name is a quota bucket ("general", "video"), not a plan name.
        M["header"].set_label(f"MiniMax {d['plan_label']}")

        # Interval
        if d["interval_total"] > 0:
            int_label = (
                f"  Used: {fmt_count(d['interval_used'])} / "
                f"{fmt_count(d['interval_total'])} requests ({d['interval_pct']}%)"
            )
        elif d["interval_pct"] is not None:
            int_label = f"  Used: {d['interval_pct']}% of 5h window"
        else:
            int_label = "  Used: --"
        M["int_details"].set_label(int_label)
        M["int_reset"].set_label(
            f"  \u21bb Resets in: {fmt_reset(d['interval_reset_ms'])}"
        )

        # Weekly
        if d["weekly_total"] > 0:
            wk_label = (
                f"  Used: {fmt_count(d['weekly_used'])} / "
                f"{fmt_count(d['weekly_total'])} requests/tokens ({d['weekly_pct']}%)"
            )
            M["wk_reset"].set_label(
                f"  \u21bb Resets in: {fmt_reset(d['weekly_reset_ms'])}"
            )
            M["wk_details"].show()
            M["wk_reset"].show()
        elif d.get("weekly_rem_pct") is not None:
            wk_label = f"  Used: {d['weekly_pct']}%"
            M["wk_reset"].set_label(
                f"  \u21bb Resets in: {fmt_reset(d['weekly_reset_ms'])}"
            )
            M["wk_details"].show()
            M["wk_reset"].show()
        elif d.get("weekly_tracked"):
            wk_label = "  Used: --"
            M["wk_details"].show()
            M["wk_reset"].hide()
        else:
            wk_label = "  Weekly limit not enabled on this plan"
            M["wk_details"].show()
            M["wk_reset"].hide()
        M["wk_details"].set_label(wk_label)

        M["model_name"].set_label(f"Plan: {d['plan_label']}")
        M["status"].set_label(f"Updated {d['ts'].strftime('%H:%M:%S')}")

    def _set_status(self, msg):
        self._mi["status"].set_label(msg)

    # ── Data fetching ──────────────────────────────────────

    def _refresh(self):
        if not self._client:
            return
        self._set_status("Refreshing...")
        self._fetch_queue.put("refresh")

    def _start_fetch_worker(self):
        if self._fetch_thread is not None and self._fetch_thread.is_alive():
            return
        self._fetch_shutdown = False

        def worker():
            while not self._fetch_shutdown:
                try:
                    self._fetch_queue.get(timeout=1)
                    if self._fetch_shutdown:
                        break
                    try:
                        data = self._client.fetch_all()
                        GLib.idle_add(self._on_data, data)
                    except APIAuthError as e:
                        GLib.idle_add(self._on_error, str(e))
                    except APIError as e:
                        GLib.idle_add(self._on_error, str(e))
                    self._fetch_queue.task_done()
                except queue.Empty:
                    continue

        self._fetch_thread = threading.Thread(target=worker, daemon=True)
        self._fetch_thread.start()

    def _on_data(self, data):
        self._data = data
        self._last_error = ""
        pct = data.get("interval_pct")
        self._indicator.set_label(_usage_label("MMX", pct), "")
        self._maybe_notify_threshold("MMX", pct)
        self._update_menu(data)
        if self._win:
            self._win.update_data(data)
        return False

    def _on_error(self, msg):
        self._indicator.set_label("MMX ERR", "")
        if msg != self._last_error:
            self._notify("MiniMax Quota Error", msg)
        self._last_error = msg
        self._set_status(self._error_status(msg))
        return False

    def _error_status(self, msg):
        if self._data and self._data.get("ts"):
            return f"Error: {msg} (last OK {self._data['ts'].strftime('%H:%M:%S')})"
        return f"Error: {msg}"

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

    def _on_open_console(self, _):
        Gtk.show_uri_on_window(None, CONSOLE_URL, Gtk.get_current_event_time())

    def _maybe_notify_threshold(self, name, pct):
        level = _threshold_level(pct)
        if not level:
            self._last_threshold_notice = ""
            return
        if level == self._last_threshold_notice:
            return
        self._last_threshold_notice = level
        self._notify(f"{name} usage {level}", f"{_usage_label(name, pct)} used")

    def _notify(self, title, body):
        notification = Gio.Notification.new(title)
        notification.set_body(body)
        self.send_notification(title.lower().replace(" ", "-"), notification)

    def _on_settings(self, _):
        def on_save(cfg):
            self._config = cfg
            save_config(self._config)
            if self._config["api_key"]:
                self._client = APIClient(self._config["api_key"])
                self._start_fetch_worker()
                self._refresh()
                self._schedule_refresh()
            else:
                self._client = None
                self._indicator.set_label("MMX ?", "")
                self._set_status("No API key configured")

        win = SettingsWindow(self, on_save)
        win.show_all()

    def _on_quit(self, _):
        if self._timer_id:
            GLib.source_remove(self._timer_id)
        self._fetch_shutdown = True
        self._fetch_queue.put("shutdown")
        if self._fetch_thread:
            self._fetch_thread.join(timeout=2)
        self.quit()


def main():
    parser = argparse.ArgumentParser(description="MiniMax quota indicator")
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="verify MiniMax API key and quota access without launching GTK",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit diagnostic output as JSON",
    )
    args = parser.parse_args()
    if args.check_auth:
        return check_auth(json_output=args.json)

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
    return app.run()


def check_auth(json_output=False):
    cfg = load_config()
    result = {
        "app": "minimax",
        "api_key_configured": bool(cfg.get("api_key")),
        "console_url": CONSOLE_URL,
    }
    if not cfg.get("api_key"):
        result.update({"fetch_ok": False, "error": "No API key configured"})
        _print_check_result("MiniMax auth check", result, json_output)
        return 1
    try:
        data = APIClient(cfg["api_key"]).fetch_all()
    except APIError as e:
        result.update({"fetch_ok": False, "error": str(e)})
        _print_check_result("MiniMax auth check", result, json_output)
        return 1
    supp_models = [m["id"] for m in data.get("supported_models", [])]
    result.update(
        {
            "fetch_ok": True,
            "plan": data.get("plan_label") or "",
            "primary_bucket": data.get("model_name") or "",
            "interval_pct_present": data.get("interval_pct") is not None,
            "weekly_tracked": bool(data.get("weekly_tracked")),
            "all_quota_buckets": len(data.get("all_models") or []),
            "supported_models": ", ".join(supp_models) if supp_models else "--",
        }
    )
    _print_check_result("MiniMax auth check", result, json_output)
    return 0


def _usage_label(prefix, pct):
    if pct is None:
        return f"{prefix} --"
    try:
        value = float(pct)
    except (TypeError, ValueError):
        return f"{prefix} --"
    marker = "!" if value >= 90 else "*" if value >= 80 else ""
    return f"{prefix} {marker}{value:.0f}%"


def _threshold_level(pct):
    try:
        value = float(pct)
    except (TypeError, ValueError):
        return ""
    if value >= 90:
        return "critical"
    if value >= 80:
        return "warning"
    return ""


def _print_check_result(title, result, json_output):
    if json_output:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(title)
    for key, value in result.items():
        print(f"{key}: {value if value not in ('', None) else '--'}")
