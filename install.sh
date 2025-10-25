#!/bin/bash
# One-command installer and runner for ref.tools API Key Generator
# Automatically cleans up everything after execution
# Use KEEP_FILES=1 to skip cleanup

set -e

TEMP_DIR=$(mktemp -d)
ORIGINAL_DIR=$(pwd)
KEEP_FILES="${KEEP_FILES:-0}"

# Cleanup function
cleanup() {
    if [ "$KEEP_FILES" = "1" ]; then
        echo ""
        echo "ℹ️  Skipping cleanup (KEEP_FILES=1)"
        echo "   Script saved at: $TEMP_DIR/ref_keygen.py"
        echo "   Run: python3 $TEMP_DIR/ref_keygen.py"
        return
    fi
    
    echo ""
    echo "🧹 Cleaning up..."
    
    # Remove temporary directory and all contents
    cd "$ORIGINAL_DIR"
    rm -rf "$TEMP_DIR"
    
    # Uninstall packages (only if we installed them)
    if [ "$INSTALLED_DEPS" = "true" ]; then
        echo "   Removing installed packages..."
        pip uninstall -y playwright aiohttp rich 2>/dev/null || true
    fi
    
    # Clear pip cache
    echo "   Clearing pip cache..."
    pip cache purge 2>/dev/null || true
    
    # Remove Playwright browsers
    echo "   Removing Playwright browsers..."
    rm -rf ~/Library/Caches/ms-playwright 2>/dev/null || true
    rm -rf ~/.cache/ms-playwright 2>/dev/null || true
    
    # Remove Python cache
    echo "   Clearing Python cache..."
    find "$ORIGINAL_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$ORIGINAL_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    echo "✨ Cleanup complete! No traces left."
}

# Set trap to cleanup on exit (success or failure)
trap cleanup EXIT

echo "🔑 ref.tools API Key Generator"
echo "================================"
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

# Change to temp directory
cd "$TEMP_DIR"

# Check if dependencies are already installed
INSTALLED_DEPS="false"
if ! python3 -c "import playwright; import aiohttp; import rich" 2>/dev/null; then
    INSTALLED_DEPS="true"
    echo "📦 Installing dependencies..."
    
    # Deactivate any active virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "   Deactivating existing virtual environment..."
        unset VIRTUAL_ENV
        export PATH=$(echo "$PATH" | sed -e 's|[^:]*\.venv[^:]*:||g' -e 's|:$||')
    fi
    
    if command -v uv &> /dev/null; then
        echo "   Using uv (faster installation)"
        uv pip install --system playwright aiohttp rich --quiet 2>/dev/null || pip install --user playwright aiohttp rich --quiet
    else
        pip install --user playwright aiohttp rich --quiet
    fi
    
    echo ""
    echo "🌐 Installing Playwright browser..."
    python3 -m playwright install chromium --quiet 2>/dev/null || python3 -m playwright install chromium
else
    echo "✓ Dependencies already installed (will not be removed)"
fi

echo ""
echo "📥 Downloading script..."
curl -sSL -o ref_keygen.py https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/get_ref_key.py

echo ""
echo "🚀 Running key generator..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the script
python3 ref_keygen.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Cleanup will happen automatically via trap
