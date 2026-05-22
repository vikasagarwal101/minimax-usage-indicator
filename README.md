# MiniMax Token Plan Usage Indicator

A GNOME panel indicator for monitoring your [MiniMax Token Plan](https://api.minimax.io) quota usage.

Shows up in your top bar as a panel indicator with a remaining quota percentage label. Click it for a detailed dropdown menu, or open the full detail window.

## Menu Preview

```
 Top bar:  🖥 MM 92%
                ┌─────────────────────────────────┐
                │ MiniMax Token Plan (abab6.5s)   │
                │─────────────────────────────────│
                │ Interval Quota (5h Window)      │
                │   Remaining: 92 / 100 requests  │
                │   ↻ Resets in: 2h 04m           │
                │─────────────────────────────────│
                │ Weekly Quota                    │
                │   Remaining: 1,850 / 2,000      │
                │   ↻ Resets in: 4d 11h           │
                │─────────────────────────────────│
                │ Plan Model: abab6.5s            │
                │─────────────────────────────────│
                │ Open Details Window             │
                │ Refresh Now                     │
                │ Settings…                       │
                │─────────────────────────────────│
                │ Updated 14:32:05                │
                │ Quit                            │
                └─────────────────────────────────┘
```

## Features

- **Panel indicator** — lives in your GNOME top bar, no window to manage.
- **Interval budget (5h window)** — tracks remaining requests and resets countdown.
- **Weekly quota** — tracks remaining weekly requests/tokens and weekly reset.
- **Plan model metadata** — displays your active subscription plan models.
- **Detail window** — full GTK window with beautiful progress bars showing remaining quotas.
- **Auto-refresh** — configurable interval (default 5 min).
- **Autostart** — can launch on login.

## Requirements

- Ubuntu 24.04+ / GNOME 45+ (tested on Ubuntu 26.04 / GNOME 50)
- Python 3.10+
- `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-ayatanaappindicator3-0.1`
- The `ubuntu-appindicators` GNOME Shell extension (pre-installed on Ubuntu)
- A MiniMax Token Plan subscription and `sk-cp-...` API key

## Install

```bash
chmod +x install.sh
./install.sh
```

This will:

1. Install system dependencies via apt
2. Create a desktop entry (shows up in Activities)
3. Optionally enable autostart on login

## Configure

On first launch, click the indicator → **Settings…** and paste your MiniMax Token Plan API key (should start with `sk-cp-`).

Or create the config file manually:

```bash
mkdir -p ~/.config/minimax-usage-widget
cp config.example.json ~/.config/minimax-usage-widget/config.json
# Then edit ~/.config/minimax-usage-widget/config.json and add your API key
```

### Config options

| Key | Default | Description |
|---|---|---|
| `api_key` | `""` | Your MiniMax Token Plan `sk-cp-...` API key |
| `refresh_interval` | `300` | Seconds between auto-refreshes |

## Run

```bash
python3 minimax-usage-indicator.py
```

## How it works

Uses the official MiniMax remains query endpoint:

| Endpoint | Data |
|---|---|
| `/v1/token_plan/remains` | Interval & weekly remaining quotas and resets |

Authentication is via `Authorization: Bearer <api-key>` header.

Panel indicator uses [Ayatana AppIndicator](https://github.com/AyatanaIndicators/libayatana-appindicator) (the GTK3 variant) via the `com.canonical.dbusmenu` protocol.

## Project structure

```
├── minimax-usage-indicator.py    # Entry point
├── lib/
│   ├── indicator.py              # MiniMaxApp: panel icon, menu, refresh loop
│   ├── api.py                    # APIClient for MiniMax remains API
│   ├── config.py                 # Config loading, formatters
│   ├── detail.py                 # DetailWindow (GTK3)
│   └── settings.py               # SettingsWindow (GTK3)
├── config.example.json
├── install.sh
├── README.md
└── LICENSE
```

## License

MIT

