# 🔑 ref.tools API Key Generator

> **One-command automated API key generation for ref.tools**

A fast, automated script that generates API keys for [ref.tools](https://ref.tools) using temporary email addresses. No signup hassle, just run and get your key!

## ⚡ Quick Start (One Command)

**Run instantly without installing:**

```bash
bash <(curl -sSL https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.sh)
```

This will:
1. Check Python version (3.10+ required)
2. Install dependencies (playwright, aiohttp, rich)
3. Download the script
4. Run it immediately

### Manual Installation

If you prefer to install dependencies manually:

```bash
pip install playwright aiohttp rich && playwright install chromium
curl -O https://raw.githubusercontent.com/yourusername/ref-tools-keygen/main/get_ref_key.py
python3 get_ref_key.py
```

## ✨ Features

- 🚀 **Fully Automated** - No manual steps required
- 📧 **Temporary Email** - Uses Guerrilla Mail API
- 🔐 **Secure** - Generates strong random passwords
- 🌐 **Proxy Support** - Optional proxy rotation (set `USE_PROXY=1`)
- 🎨 **Beautiful UI** - Rich terminal interface
- ⚡ **Fast** - Async operations for speed
- 🐛 **Debug Mode** - Detailed logging (`DEBUG=1`)

## 🎮 Usage Options

**Basic usage:**
```bash
python3 get_ref_key.py
```

**With proxy support:**
```bash
USE_PROXY=1 python3 get_ref_key.py
```

**Debug mode (see browser):**
```bash
DEBUG=1 python3 get_ref_key.py
```

## 📦 Requirements

- Python 3.10+
- `playwright`, `aiohttp`, `rich` (auto-installed above)

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

1. Generates temporary email via Guerrilla Mail
2. Automates ref.tools signup with Playwright
3. Clicks verification email button
4. Monitors inbox for verification email
5. Confirms email and extracts API key

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
