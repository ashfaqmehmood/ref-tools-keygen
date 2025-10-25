#!/usr/bin/env bash
# ============================================================
#  🔑 ref.tools API Key Generator Installer
#  Universal installer for macOS/Linux (auto-cleanup)
#  Usage:
#     bash <(curl -sSL https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.sh)
#
#  Windows users:
#     iwr -useb https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.ps1 | iex
# ============================================================

set -e

# ------------------------------------------------------------
# Detect OS
# ------------------------------------------------------------
OS="$(uname -s 2>/dev/null || echo Unknown)"
case "$OS" in
  *CYGWIN*|*MINGW*|*MSYS*|*Windows*)
    echo "⚠️  You appear to be on Windows."
    echo "👉 Please run this command in PowerShell instead:"
    echo "   iwr -useb https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.ps1 | iex"
    exit 0
    ;;
esac

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
KEEP_FILES="${KEEP_FILES:-0}"
TEMP_DIR="$(mktemp -d)"
ORIG_DIR="$(pwd)"
SCRIPT_URL="https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/get_ref_key.py"
SCRIPT_FILE="$TEMP_DIR/get_ref_key.py"

# ------------------------------------------------------------
# Cleanup Handler
# ------------------------------------------------------------
cleanup() {
  cd "$ORIG_DIR"
  if [ "$KEEP_FILES" = "1" ]; then
    echo ""
    echo "ℹ️  Skipping cleanup (KEEP_FILES=1)"
    echo "   Script saved at: $SCRIPT_FILE"
    return
  fi

  echo ""
  echo "🧹 Cleaning up temporary files..."
  rm -rf "$TEMP_DIR" 2>/dev/null || true
  echo "✨ Cleanup complete!"
}
trap cleanup EXIT

# ------------------------------------------------------------
# Python Check
# ------------------------------------------------------------
echo "🔑 ref.tools API Key Generator"
echo "================================"
echo ""

if ! command -v python3 &> /dev/null; then
  echo "❌ Python 3 is not installed."
  echo "   Please install Python 3.8+ and retry."
  exit 1
fi

PYV=$(python3 -c 'import sys; print(sys.version_info[:2] >= (3,8))')
if [ "$PYV" != "True" ]; then
  echo "❌ Python 3.8+ required."
  exit 1
fi

echo "✓ Python detected ($(python3 -V))"
echo ""

# ------------------------------------------------------------
# Download Script
# ------------------------------------------------------------
echo "📥 Downloading Python script..."
curl -sSL -o "$SCRIPT_FILE" "$SCRIPT_URL"

# ------------------------------------------------------------
# Run Script
# ------------------------------------------------------------
echo ""
echo "🚀 Running the API Key Generator..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

KEEP_FILES="$KEEP_FILES" RTK_TEMP_ROOT="$TEMP_DIR/run" python3 "$SCRIPT_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Finished!"