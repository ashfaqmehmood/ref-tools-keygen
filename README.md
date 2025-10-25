# 🔑 ref.tools API Key Generator

> **One-command automated API key generation for ref.tools**

A fast, automated script that generates API keys for [ref.tools](https://ref.tools) using temporary email addresses. No signup hassle, just run and get your key!

**✨ Features:** Fully automated | Auto-cleanup | Zero traces | One command

## ⚡ Quick Start (One Command)

### 🧩 macOS & Linux (One Command)

```bash
bash <(curl -sSL https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.sh)
```

### 🪟 Windows (PowerShell)

```powershell
iwr -useb https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.ps1 | iex
```

**What happens:**
1. ✅ Checks Python version (3.8+ required)
2. ✅ Creates isolated virtualenv in temp directory
3. ✅ Installs dependencies (playwright, aiohttp, rich)
4. ✅ Downloads Chromium browser (isolated)
5. ✅ Generates your API key
6. ✅ **Automatically cleans everything** (venv, packages, browsers, temp files)

**No traces left behind!** Perfect for one-time use. 🧹

### Manual Installation (Persistent)

If you want to keep the script and run it multiple times:

```bash
pip install playwright aiohttp rich && playwright install chromium
curl -O https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/get_ref_key.py
python3 get_ref_key.py
```

## ✨ Features

- 🚀 **Fully Automated** - No manual steps required
- 🧹 **Auto-Cleanup** - Removes all dependencies, cache, and traces after run
- �️ **Cross-Platform** - Works on macOS, Linux, and Windows
- 🔒 **Isolated Environment** - Uses temp virtualenv, doesn't affect your system
- �📧 **Temporary Email** - Uses Guerrilla Mail API
- 🔐 **Secure** - Generates strong random passwords
- 🌐 **Proxy Support** - Optional proxy rotation (set `USE_PROXY=1`)
- 🎨 **Beautiful UI** - Rich terminal interface
- ⚡ **Fast** - Async operations for speed
- 🐛 **Debug Mode** - Detailed logging (`DEBUG=1`)
- 🗑️ **Zero Traces** - Completely cleans up after execution
- 🐍 **Self-Bootstrapping** - Installs its own dependencies automatically

## 🎮 Usage Options

**One-time use with auto-cleanup (recommended):**

```bash
# macOS/Linux
bash <(curl -sSL https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.sh)

# Windows
iwr -useb https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.ps1 | iex
```

### 🔍 Optional Environment Flags

| Variable | Description | Example |
|----------|-------------|---------|
| `DEBUG=1` | Enables detailed logs & screenshots | `DEBUG=1 bash <(curl -sSL ...)` |
| `USE_PROXY=1` | Enable proxy rotation | `USE_PROXY=1 bash <(curl -sSL ...)` |
| `KEEP_FILES=1` | Retain files after completion | `KEEP_FILES=1 bash <(curl -sSL ...)` |

**Examples:**

```bash
# macOS/Linux with proxy support
USE_PROXY=1 bash <(curl -sSL https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.sh)

# Windows with debug mode
$env:DEBUG="1"; iwr -useb https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.ps1 | iex

# Keep files for inspection (won't auto-cleanup)
KEEP_FILES=1 bash <(curl -sSL https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.sh)
```

**If you downloaded the script manually:**
```bash
# Basic usage (self-bootstrapping)
python3 get_ref_key.py

# With proxy support
USE_PROXY=1 python3 get_ref_key.py

# Debug mode (see browser)
DEBUG=1 python3 get_ref_key.py
```

## 📦 Requirements

- Python 3.8+
- `playwright`, `aiohttp`, `rich` (auto-installed in isolated venv)

## 🎯 Output Example

```
╔════════════════════════════════════════════════════╗
║ 🔑 ref.tools API Key Generator                     ║
║ Automated API key generation using temporary email ║
╚════════════════════════════════════════════════════╝

✓ Email generated: example@guerrillamailblock.com
✓ Signup successful
✓ Verification email requested
✓ Verification email received
✓ Email confirmed

============================================================
            ✨ SUCCESS! API Key Generated ✨
============================================================

╭───────────────┬──────────────────────────────╮
│ 🔑 API Key    │ ref-abc123def456             │
│ 📧 Email      │ example@guerrillamail.com    │
│ 🔒 Password   │ Abc123XYZ!@#                 │
╰───────────────┴──────────────────────────────╯
```

## 🔧 How It Works

1. Creates temporary directory for isolated execution
2. Generates temporary email via Guerrilla Mail
3. Automates ref.tools signup with Playwright
4. Clicks verification email button
5. Monitors inbox for verification email
6. Confirms email and extracts API key
7. **Auto-cleanup:** Removes all dependencies, browsers, cache, and temp files

## 🧹 What Gets Cleaned Up

The one-command installer automatically removes:
- ✅ Isolated virtual environment (created in temp)
- ✅ Downloaded script files
- ✅ Installed Python packages (playwright, aiohttp, rich)
- ✅ Playwright browser binaries (~400MB, isolated in temp)
- ✅ Python `__pycache__` directories
- ✅ All temporary directories

**Result:** Your system is left exactly as it was before running the command! 🎯

## 🌐 Proxy Support

Enable proxy rotation to avoid rate limiting:

```bash
USE_PROXY=1 python3 get_ref_key.py
```

Proxies are fetched from [TheSpeedX/PROXY-List](https://github.com/TheSpeedX/PROXY-List).

## 🐛 Troubleshooting

**Enable debug mode** to see detailed logs:

```bash
DEBUG=1 python3 get_ref_key.py
```

This will:
- Show browser window
- Print detailed logs
- Save screenshots for inspection

## ⚠️ Disclaimer

For educational purposes only. Use responsibly and respect ref.tools' Terms of Service.

---

## � Getting Started

After installation, you'll have a `ref_keygen.py` file. Run it with:

```bash
python3 ref_keygen.py
```

Your API key will be displayed in a beautiful formatted table. Save your credentials securely!

---

**⭐ Star this repo if you find it useful!**

Made for the dev community 🤝
