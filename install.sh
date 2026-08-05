#!/bin/bash
set -e

APP_NAME="MiniMax Quota Indicator"
APP_ID="com.minimax.usage-widget"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/minimax-usage-indicator"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
APP_DIR="${HOME}/.local/share/applications"
AUTOSTART_DIR="${HOME}/.config/autostart"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║    MiniMax Quota Indicator Installer     ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ── Dependencies ──────────────────────────────────────────────

echo "[1/5] Checking system dependencies..."

DEPS="python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1"
MISSING=""
for dep in $DEPS; do
    if ! dpkg -l "$dep" 2>/dev/null | grep -q '^ii'; then
        MISSING="$MISSING $dep"
    fi
done

if [ -n "$MISSING" ]; then
    echo "  Installing:$MISSING"
    pkexec apt-get install -y -qq $MISSING 2>/dev/null || {
        echo "  ⚠ Could not auto-install. Please run:"
        echo "    sudo apt-get install$MISSING"
    }
else
    echo "  ✓ All dependencies present"
fi

# ── Copy files ────────────────────────────────────────────────

echo "[2/5] Installing application files..."

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Copy Python modules
cp -r "$SCRIPT_DIR/lib" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/minimax-usage-indicator.py" "$INSTALL_DIR/"

# Make entry point executable
chmod +x "$INSTALL_DIR/minimax-usage-indicator.py"

echo "  ✓ Installed to $INSTALL_DIR"

# ── Install icons ─────────────────────────────────────────────

echo "[3/4] Installing application icon..."

mkdir -p "$ICON_DIR"
cp "$SCRIPT_DIR/minimax-usage-indicator.svg" "$ICON_DIR/${APP_ID}.svg"
cp "$SCRIPT_DIR/panel-icon.svg" "$INSTALL_DIR/panel-icon.svg"
cp "$SCRIPT_DIR/minimax-usage-indicator.svg" "$INSTALL_DIR/minimax-usage-indicator.svg"
gtk-update-icon-cache -f "${HOME}/.local/share/icons/hicolor/" 2>/dev/null || true

echo "  ✓ Icon installed"

# ── Desktop entry ─────────────────────────────────────────────

echo "[4/4] Creating launcher..."

mkdir -p "$APP_DIR"
cat > "$APP_DIR/${APP_ID}.desktop" << EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Panel indicator for MiniMax Token Plan quota usage
Exec=python3 ${INSTALL_DIR}/minimax-usage-indicator.py
Icon=${APP_ID}
Terminal=false
Categories=Utility;System;
Keywords=minimax;quota;tokens;coding plan;
StartupNotify=false
StartupWMClass=${APP_ID}
EOF

update-desktop-database "$APP_DIR" 2>/dev/null || true
echo "  ✓ Launcher created"

# ── Autostart ─────────────────────────────────────────────────

echo ""
echo "  Autostart"
read -p "Start on login? [Y/n] " -r
AUTOSTART_REPLY="${REPLY:-y}"
echo

if [[ $AUTOSTART_REPLY =~ ^[Yy]$ ]]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$APP_DIR/${APP_ID}.desktop" "$AUTOSTART_DIR/${APP_ID}.desktop"
    echo "  ✓ Autostart enabled"
else
    rm -f "$AUTOSTART_DIR/${APP_ID}.desktop"
    echo "  - Autostart skipped"
fi

# ── Launch ────────────────────────────────────────────────────

read -p "Launch now? [Y/n] " -r
LAUNCH_REPLY="${REPLY:-y}"
echo

if [[ $LAUNCH_REPLY =~ ^[Yy]$ ]]; then
    # Kill any existing instances
    pkill -f minimax-usage-indicator.py 2>/dev/null || true
    sleep 1
    setsid python3 "$INSTALL_DIR/minimax-usage-indicator.py" </dev/null >/dev/null 2>&1 &
    echo "  ✓ Launched — look for the icon in your top panel bar"
fi

echo ""
echo "  ─────────────────────────────────────────"
echo "  Done! You can also search '$APP_NAME'"
echo "  in Activities to launch it later."
echo ""

