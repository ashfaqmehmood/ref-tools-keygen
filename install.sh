#!/bin/bash
# One-command installer for ref.tools API Key Generator

set -e

echo "🔑 ref.tools API Key Generator - Quick Install"
echo "================================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "   Please install Python 3.10+ first"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo "❌ Error: Python $REQUIRED_VERSION+ required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
if command -v uv &> /dev/null; then
    echo "   Using uv (faster installation)"
    uv pip install playwright aiohttp rich
else
    pip install playwright aiohttp rich
fi

echo ""
echo "🌐 Installing Playwright browser..."
playwright install chromium

echo ""
echo "📥 Downloading script..."
curl -sSL -o ref_keygen.py https://raw.githubusercontent.com/yourusername/ref-tools-keygen/main/get_ref_key.py
chmod +x ref_keygen.py

echo ""
echo "✨ Installation complete!"
echo ""
echo "🚀 Run now:"
echo "   python3 ref_keygen.py"
echo ""
echo "📚 Usage:"
echo "   Basic:           python3 ref_keygen.py"
echo "   With proxy:      USE_PROXY=1 python3 ref_keygen.py"
echo "   Debug mode:      DEBUG=1 python3 ref_keygen.py"
echo ""
