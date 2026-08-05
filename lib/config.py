import json
import os
from datetime import datetime

CONFIG_DIR = os.path.expanduser("~/.config/minimax-usage-widget")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULTS = {"api_key": "", "refresh_interval": 300}


def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                for k, v in DEFAULTS.items():
                    cfg.setdefault(k, v)
                return cfg
    except Exception:
        pass
    return dict(DEFAULTS)


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def fmt_tokens(n):
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_count(n):
    return f"{n:,}" if n else "0"


def fmt_reset(ts_ms):
    if not ts_ms:
        return "--"
    dt = datetime.fromtimestamp(ts_ms / 1000)
    diff = dt - datetime.now()
    total_seconds = int(diff.total_seconds())
    if total_seconds < 0:
        return "now"

    d, rem = divmod(total_seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)

    if d > 0:
        return f"{d}d {h}h"
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m {s}s"
