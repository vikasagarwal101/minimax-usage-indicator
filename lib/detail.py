import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk

from .config import fmt_count, fmt_reset


class DetailWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(title="MiniMax Quota Details", application=app)
        self.set_default_size(460, 560)
        self.data = None
        self._w = {}

        self._build()

    def _build(self):
        screen = Gdk.Screen.get_default()
        css = Gtk.CssProvider()
        css.load_from_data(b"""
            .stat-frame {
                padding: 14px 18px;
                border-radius: 8px;
                background: alpha(@theme_fg_color, 0.05);
                margin-bottom: 8px;
            }
            .stat-title { font-weight: bold; font-size: 1.0em; }
            .stat-value { font-size: 1.8em; font-weight: bold; }
            .dim { opacity: 0.55; }
            progressbar trough { min-height: 8px; border-radius: 4px; }
            progressbar progress { min-height: 8px; border-radius: 4px; }
            .model-row {
                padding: 8px 12px;
                border-radius: 6px;
                background: alpha(@theme_fg_color, 0.02);
                margin-bottom: 6px;
            }
            .model-name { font-weight: bold; font-size: 0.95em; }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

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
        
        self._w["int_details"] = Gtk.Label(label="Remaining: -- / -- requests", xalign=0)
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
        
        self._w["wk_details"] = Gtk.Label(label="Remaining: -- / -- requests/tokens", xalign=0)
        f.pack_start(self._w["wk_details"], False, False, 0)
        
        self._w["wk_period"] = Gtk.Label(label="Cycle: --", xalign=0)
        self._w["wk_period"].get_style_context().add_class("dim")
        f.pack_start(self._w["wk_period"], False, False, 0)
        
        self._w["wk_reset"] = Gtk.Label(label="Resets in: --", xalign=0)
        self._w["wk_reset"].get_style_context().add_class("dim")
        f.pack_start(self._w["wk_reset"], False, False, 0)

    def _build_all_models(self, parent):
        f = self._frame(parent, "All Subscription Quotas")
        self._w["all_models_box"] = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        f.pack_start(self._w["all_models_box"], False, False, 4)

    def _build_status(self, parent):
        self._w["status"] = Gtk.Label(label="")
        self._w["status"].get_style_context().add_class("dim")
        parent.pack_start(self._w["status"], False, False, 4)

    def update_data(self, d):
        self.data = d
        W = self._w

        # Interval
        int_pct = d["interval_pct"]
        W["int_lbl"].set_label(f"{int_pct}% Used ({d['model_name']})")
        W["int_bar"].set_fraction(min(int_pct / 100, 1.0))
        W["int_details"].set_label(
            f"Used: {fmt_count(d['interval_used'])} / "
            f"{fmt_count(d['interval_total'])} requests ({fmt_count(d['interval_remains'])} left)"
        )
        
        start_str = d["interval_start"].strftime("%H:%M") if d["interval_start"] else "--"
        end_str = d["interval_end"].strftime("%H:%M") if d["interval_end"] else "--"
        W["int_period"].set_label(f"Active Window: {start_str} - {end_str}")
        W["int_reset"].set_label(f"Resets in: {fmt_reset(d['interval_reset_ms'])}")

        # Weekly
        wk_pct = d["weekly_pct"]
        W["wk_lbl"].set_label(f"{wk_pct}% Used" if d["weekly_total"] > 0 else "Unlimited Weekly")
        W["wk_bar"].set_fraction(min(wk_pct / 100, 1.0))
        if d["weekly_total"] > 0:
            W["wk_details"].set_label(
                f"Used: {fmt_count(d['weekly_used'])} / "
                f"{fmt_count(d['weekly_total'])} requests/tokens ({fmt_count(d['weekly_remains'])} left)"
            )
            wk_start_str = d["weekly_start"].strftime("%b %d") if d["weekly_start"] else "--"
            wk_end_str = d["weekly_end"].strftime("%b %d") if d["weekly_end"] else "--"
            W["wk_period"].set_label(f"Cycle: {wk_start_str} - {wk_end_str}")
            W["wk_reset"].set_label(f"Resets in: {fmt_reset(d['weekly_reset_ms'])}")
            W["wk_period"].show()
            W["wk_reset"].show()
        else:
            W["wk_details"].set_label("No weekly limit for this subscription tier")
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

            pct_lbl = Gtk.Label(label=f"{m['interval_used_pct']}% Used")
            pct_lbl.get_style_context().add_class("dim")
            pct_lbl.set_xalign(1)
            lbl_box.pack_end(pct_lbl, False, False, 0)

            row.pack_start(lbl_box, False, False, 0)

            bar = Gtk.ProgressBar()
            bar.set_fraction(m["interval_used_pct"] / 100)
            row.pack_start(bar, False, False, 0)

            m_used = m["interval_total"] - m["interval_remains"]
            det_str = f"Interval Used: {fmt_count(m_used)} / {fmt_count(m['interval_total'])} ({fmt_count(m['interval_remains'])} left)"
            if m["weekly_total"] > 0:
                m_wk_used = m["weekly_total"] - m["weekly_remains"]
                det_str += f"  ·  Weekly Used: {fmt_count(m_wk_used)} / {fmt_count(m['weekly_total'])} ({fmt_count(m['weekly_remains'])} left)"
            
            details_lbl = Gtk.Label(label=det_str, xalign=0)
            details_lbl.get_style_context().add_class("dim")
            row.pack_start(details_lbl, False, False, 0)

            W["all_models_box"].pack_start(row, False, False, 0)

        W["all_models_box"].show_all()

        # Status
        W["status"].set_label(f"Updated {d['ts'].strftime('%H:%M:%S')}")
        self.show_all()

