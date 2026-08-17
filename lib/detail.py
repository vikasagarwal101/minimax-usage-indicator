import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk

from .config import fmt_count, fmt_reset

# Shared CSS provider to avoid leaking per-window providers
_shared_css_provider = None
_css_applied = False


def _get_css_provider():
    global _shared_css_provider, _css_applied
    if _shared_css_provider is None:
        _shared_css_provider = Gtk.CssProvider()
        _shared_css_provider.load_from_data(
            b"""
            .stat-frame {
                padding: 14px 18px;
                border-radius: 8px;
                background: alpha(@theme_fg_color, 0.05);
                margin-bottom: 8px;
            }
            .stat-title { font-weight: bold; font-size: 1.0em; }
            .stat-value { font-size: 1.8em; font-weight: bold; }
            .dim { opacity: 0.65; font-size: 0.9em; }
            progressbar trough { min-height: 8px; border-radius: 4px; }
            progressbar progress { min-height: 8px; border-radius: 4px; }
            .model-row {
                padding: 8px 12px;
                border-radius: 6px;
                background: alpha(@theme_fg_color, 0.02);
                margin-bottom: 6px;
            }
            .model-name { font-weight: bold; font-size: 0.95em; }
            .badge {
                padding: 1px 6px;
                border-radius: 4px;
                background: alpha(@theme_fg_color, 0.08);
                font-size: 0.8em;
                margin-left: 4px;
            }
        """
        )
    if not _css_applied:
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen, _shared_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            _css_applied = True
    return _shared_css_provider


class DetailWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(title="MiniMax Quota Details", application=app)
        self.set_default_size(480, 620)
        self.data = None
        self._w = {}

        _get_css_provider()
        self._build()

    def _build(self):
        header = Gtk.HeaderBar(title="MiniMax Quota Details", show_close_button=True)
        self.set_titlebar(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        self._build_interval(box)
        self._build_weekly(box)
        self._build_all_models(box)
        self._build_supported_models(box)
        self._build_status(box)

        scroll.add(box)
        self.add(scroll)

    def _frame(self, parent, title):
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.get_style_context().add_class("stat-frame")
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.get_style_context().add_class("stat-title")
        frame.pack_start(lbl, False, False, 0)
        parent.pack_start(frame, False, False, 0)
        return frame

    def _build_interval(self, parent):
        f = self._frame(parent, "Interval Quota (5h Rolling Window)")

        self._w["int_lbl"] = Gtk.Label(label="--%")
        self._w["int_lbl"].get_style_context().add_class("stat-value")
        self._w["int_lbl"].set_xalign(0)
        f.pack_start(self._w["int_lbl"], False, False, 2)

        self._w["int_bar"] = Gtk.ProgressBar()
        f.pack_start(self._w["int_bar"], False, False, 2)

        self._w["int_details"] = Gtk.Label(
            label="Remaining: -- / -- requests", xalign=0
        )
        f.pack_start(self._w["int_details"], False, False, 0)

        self._w["int_period"] = Gtk.Label(label="Window: --", xalign=0)
        self._w["int_period"].get_style_context().add_class("dim")
        f.pack_start(self._w["int_period"], False, False, 0)

        self._w["int_reset"] = Gtk.Label(label="Resets in: --", xalign=0)
        self._w["int_reset"].get_style_context().add_class("dim")
        f.pack_start(self._w["int_reset"], False, False, 0)

    def _build_weekly(self, parent):
        f = self._frame(parent, "Weekly Quota")

        self._w["wk_lbl"] = Gtk.Label(label="--%")
        self._w["wk_lbl"].get_style_context().add_class("stat-value")
        self._w["wk_lbl"].set_xalign(0)
        f.pack_start(self._w["wk_lbl"], False, False, 2)

        self._w["wk_bar"] = Gtk.ProgressBar()
        f.pack_start(self._w["wk_bar"], False, False, 2)

        self._w["wk_details"] = Gtk.Label(
            label="Remaining: -- / -- requests/tokens", xalign=0
        )
        f.pack_start(self._w["wk_details"], False, False, 0)

        self._w["wk_period"] = Gtk.Label(label="Cycle: --", xalign=0)
        self._w["wk_period"].get_style_context().add_class("dim")
        f.pack_start(self._w["wk_period"], False, False, 0)

        self._w["wk_reset"] = Gtk.Label(label="Resets in: --", xalign=0)
        self._w["wk_reset"].get_style_context().add_class("dim")
        f.pack_start(self._w["wk_reset"], False, False, 0)

    def _build_all_models(self, parent):
        f = self._frame(parent, "Subscription Quota Buckets")
        self._w["all_models_box"] = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=6
        )
        f.pack_start(self._w["all_models_box"], False, False, 4)

    def _build_supported_models(self, parent):
        f = self._frame(parent, "Supported Models (GET /v1/models)")
        self._w["supp_models_box"] = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        f.pack_start(self._w["supp_models_box"], False, False, 4)

    def _build_status(self, parent):
        self._w["status"] = Gtk.Label(label="")
        self._w["status"].get_style_context().add_class("dim")
        parent.pack_start(self._w["status"], False, False, 4)

    def update_data(self, d):
        self.data = d
        W = self._w
        bucket = d["model_name"]

        # Interval
        int_pct = d.get("interval_pct")
        if int_pct is not None:
            W["int_lbl"].set_label(f"{int_pct}% Used ({bucket})")
            W["int_bar"].set_fraction(min(int_pct / 100, 1.0))
        else:
            W["int_lbl"].set_label(f"--% Used ({bucket})")
            W["int_bar"].set_fraction(0.0)
        if d["interval_total"] > 0:
            W["int_details"].set_label(
                f"Used: {fmt_count(d['interval_used'])} / "
                f"{fmt_count(d['interval_total'])} requests "
                f"({fmt_count(d['interval_remains'])} left)"
            )
        elif int_pct is not None:
            W["int_details"].set_label(
                f"Used: {int_pct}% of 5h window ({d.get('interval_rem_pct', 100 - int_pct)}% remaining)"
            )
        else:
            W["int_details"].set_label("Used: --")

        start_str = (
            d["interval_start"].strftime("%H:%M") if d["interval_start"] else "--"
        )
        end_str = d["interval_end"].strftime("%H:%M") if d["interval_end"] else "--"
        W["int_period"].set_label(f"Active Window: {start_str} - {end_str}")
        W["int_reset"].set_label(f"Resets in: {fmt_reset(d['interval_reset_ms'])}")

        # Weekly
        wk_pct = d.get("weekly_pct")
        if d["weekly_total"] > 0:
            W["wk_lbl"].set_label(
                f"{wk_pct}% Used" if wk_pct is not None else "--% Used"
            )
            W["wk_bar"].set_fraction(
                min(wk_pct / 100, 1.0) if wk_pct is not None else 0.0
            )
            W["wk_details"].set_label(
                f"Used: {fmt_count(d['weekly_used'])} / "
                f"{fmt_count(d['weekly_total'])} requests/tokens "
                f"({fmt_count(d['weekly_remains'])} left)"
            )
            wk_start_str = (
                d["weekly_start"].strftime("%b %d") if d["weekly_start"] else "--"
            )
            wk_end_str = (
                d["weekly_end"].strftime("%b %d") if d["weekly_end"] else "--"
            )
            W["wk_period"].set_label(f"Cycle: {wk_start_str} - {wk_end_str}")
            W["wk_reset"].set_label(f"Resets in: {fmt_reset(d['weekly_reset_ms'])}")
            W["wk_period"].show()
            W["wk_reset"].show()
        elif wk_pct is not None:
            W["wk_lbl"].set_label(f"{wk_pct}% Used")
            W["wk_bar"].set_fraction(min(wk_pct / 100, 1.0))
            W["wk_details"].set_label(f"Used: {wk_pct}% (count not exposed)")
            W["wk_period"].hide()
            W["wk_reset"].set_label(f"Resets in: {fmt_reset(d['weekly_reset_ms'])}")
            W["wk_reset"].show()
        elif d.get("weekly_tracked"):
            W["wk_lbl"].set_label("--% Used")
            W["wk_bar"].set_fraction(0.0)
            W["wk_details"].set_label("Used: --")
            W["wk_period"].hide()
            W["wk_reset"].hide()
        else:
            W["wk_lbl"].set_label("Weekly limit not enabled")
            W["wk_bar"].set_fraction(0.0)
            W["wk_details"].set_label("No weekly limit on this subscription")
            W["wk_period"].hide()
            W["wk_reset"].hide()

        # All Active Quotas List
        for child in W["all_models_box"].get_children():
            W["all_models_box"].remove(child)

        for m in d.get("all_models", []):
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            row.get_style_context().add_class("model-row")

            lbl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            name_lbl = Gtk.Label(label=m["name"])
            name_lbl.get_style_context().add_class("model-name")
            name_lbl.set_xalign(0)
            lbl_box.pack_start(name_lbl, True, True, 0)

            i_pct = m.get("interval_pct")
            pct_text = f"{i_pct}% Used" if i_pct is not None else "--% Used"
            pct_lbl = Gtk.Label(label=pct_text)
            pct_lbl.get_style_context().add_class("dim")
            pct_lbl.set_xalign(1)
            lbl_box.pack_end(pct_lbl, False, False, 0)

            row.pack_start(lbl_box, False, False, 0)

            bar = Gtk.ProgressBar()
            bar.set_fraction(min(i_pct / 100, 1.0) if i_pct is not None else 0.0)
            row.pack_start(bar, False, False, 0)

            if m["interval_total"] > 0 and m.get("interval_remains") is not None:
                m_used = m["interval_total"] - m["interval_remains"]
                det_str = (
                    f"Interval: {fmt_count(m_used)} / "
                    f"{fmt_count(m['interval_total'])} "
                    f"({fmt_count(m['interval_remains'])} left)"
                )
            elif i_pct is not None:
                det_str = f"Interval: {i_pct}% used ({m.get('interval_rem_pct', 100 - i_pct)}% remaining)"
            else:
                det_str = "Interval: --"

            if m["weekly_total"] > 0 and m.get("weekly_remains") is not None:
                m_wk_used = m["weekly_total"] - m["weekly_remains"]
                det_str += (
                    f"  ·  Weekly: {fmt_count(m_wk_used)} / "
                    f"{fmt_count(m['weekly_total'])} "
                    f"({fmt_count(m['weekly_remains'])} left)"
                )
            elif m.get("weekly_pct") is not None:
                det_str += f"  ·  Weekly: {m['weekly_pct']}% used"

            details_lbl = Gtk.Label(label=det_str, xalign=0)
            details_lbl.get_style_context().add_class("dim")
            row.pack_start(details_lbl, False, False, 0)

            W["all_models_box"].pack_start(row, False, False, 0)

        W["all_models_box"].show_all()

        # Supported Models List
        for child in W["supp_models_box"].get_children():
            W["supp_models_box"].remove(child)

        supp_models = d.get("supported_models") or []
        for sm in supp_models:
            m_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            m_id = sm.get("id", "")
            lbl = Gtk.Label(label=m_id, xalign=0)
            lbl.get_style_context().add_class("dim")
            m_row.pack_start(lbl, False, False, 0)

            if "M3" in m_id:
                b = Gtk.Label(label="Flagship", xalign=0.5)
                b.get_style_context().add_class("badge")
                m_row.pack_start(b, False, False, 0)
            elif "highspeed" in m_id.lower():
                b = Gtk.Label(label="Highspeed", xalign=0.5)
                b.get_style_context().add_class("badge")
                m_row.pack_start(b, False, False, 0)

            W["supp_models_box"].pack_start(m_row, False, False, 0)
        W["supp_models_box"].show_all()

        # Status
        W["status"].set_label(f"Updated {d['ts'].strftime('%H:%M:%S')}")
        self.show_all()
