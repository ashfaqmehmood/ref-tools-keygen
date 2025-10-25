#!/usr/bin/env python3
"""
ref.tools API Key Generator (self-bootstrapping, cross-platform, zero-trace)

Usage (macOS/Linux):
  curl -sSL https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/get_ref_key.py | python3 -

Usage (Windows PowerShell):
  iwr -useb https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/get_ref_key.py | py -3 -

Behavior:
- Creates an isolated temp directory and virtualenv
- Installs playwright, aiohttp, rich into that venv
- Installs Chromium browser into the temp directory (PLAYWRIGHT_BROWSERS_PATH)
- Runs the signup/verification/key extraction flow
- Prints the API key and credentials
- Schedules a background cleanup to remove ALL temp files (venv, browsers, pycache)
- Set KEEP_FILES=1 to keep files for debugging

Notes:
- Requires Python 3.8+ (wider support than 3.10)
- Proxy support: set USE_PROXY=1
- Debug mode: set DEBUG=1 (writes debug artifacts to temp/debug)
"""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import string
import random
import sys
import tempfile
import subprocess
import shutil
import platform
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

# ------------------------------ Config ---------------------------------

REQUIRED_PYTHON = (3, 8)
PKGS = ["playwright>=1.50.0", "aiohttp>=3.11.0", "rich>=13.9.0"]
BROWSER_CHANNEL = "chromium"  # playwright install chromium
EMAIL_CHECK_INTERVAL = 3
MAX_EMAIL_WAIT_TIME = 120
SIGNUP_MAX_RETRIES = 3
SIGNUP_RETRY_DELAY = 5
MAX_PROXY_RETRIES = 5

GUERRILLA_MAIL_API = "https://api.guerrillamail.com/ajax.php"
REF_TOOLS_SIGNUP = "https://ref.tools/signup"
REF_TOOLS_DASHBOARD = "https://ref.tools/dashboard"
REF_TOOLS_KEYS = "https://ref.tools/keys"

PROXY_LIST_URLS = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
]

# Respect user-provided envs
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
USE_PROXY = os.environ.get("USE_PROXY", "").lower() in ("1", "true", "yes")
KEEP_FILES = os.environ.get("KEEP_FILES", "").lower() in ("1", "true", "yes")

# Globals that will be filled after bootstrap
console = None  # rich.console.Console
box = None
aiohttp = None
async_playwright = None
Browser = None
BrowserContext = None
Page = None

# --------------------------- Bootstrap layer ---------------------------


def ensure_python_version():
    if sys.version_info < REQUIRED_PYTHON:
        v = ".".join(map(str, REQUIRED_PYTHON))
        print(f"❌ Python {v}+ required (found {sys.version.split()[0]})")
        sys.exit(1)


def make_temp_root() -> Path:
    # Use RTK_TEMP_ROOT if provided (installers can control location)
    root = os.environ.get("RTK_TEMP_ROOT")
    if root:
        p = Path(root).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return Path(tempfile.mkdtemp(prefix="refkeygen_")).resolve()


def venv_paths(venv_dir: Path) -> Dict[str, Path]:
    if platform.system().lower().startswith("win"):
        py = venv_dir / "Scripts" / "python.exe"
        pip = venv_dir / "Scripts" / "pip.exe"
        bin_dir = venv_dir / "Scripts"
        site_packages = venv_dir / "Lib" / "site-packages"
    else:
        py = venv_dir / "bin" / "python3"
        pip = venv_dir / "bin" / "pip"
        bin_dir = venv_dir / "bin"
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = venv_dir / "lib" / pyver / "site-packages"
    return {
        "python": py,
        "pip": pip,
        "bin_dir": bin_dir,
        "site_packages": site_packages,
    }


def run_cmd(cmd: List[str], env: Optional[Dict[str, str]] = None):
    result = subprocess.run(cmd, env=env, check=True)
    return result.returncode


def bootstrap(temp_root: Path) -> Dict[str, Path]:
    """
    Create an ephemeral venv and install dependencies + browser into temp_root.
    Returns a dict with useful paths.
    """
    venv_dir = temp_root / "venv"
    venv_dir.mkdir(parents=True, exist_ok=True)
    # Avoid pip caches touching global dirs
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_CACHE_DIR"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(temp_root / "pw-browsers")
    env["PYTHONNOUSERSITE"] = "1"

    # Create venv
    run_cmd([sys.executable, "-m", "venv", str(venv_dir)], env=env)
    vp = venv_paths(venv_dir)

    # Install packages into venv
    pkgs = list(PKGS)
    try:
        run_cmd([str(vp["python"]), "-m", "pip", "install", "-q"] + pkgs, env=env)
    except Exception:
        # Retry without -q for diagnostics
        run_cmd([str(vp["python"]), "-m", "pip", "install"] + pkgs, env=env)

    # Install chromium browser into temp_root
    try:
        run_cmd(
            [str(vp["python"]), "-m", "playwright", "install", BROWSER_CHANNEL, "-q"],
            env=env,
        )
    except Exception:
        run_cmd(
            [str(vp["python"]), "-m", "playwright", "install", BROWSER_CHANNEL],
            env=env,
        )

    # Prepare current process to import from venv without re-exec
    # Important: we will clean up via a background reaper after exit.
    os.environ.update(env)
    # Prepend venv bin to PATH so playwright CLI and other shims are found
    os.environ["PATH"] = f'{vp["bin_dir"]}{os.pathsep}{os.environ.get("PATH","")}'
    # Load site-packages from venv
    if str(vp["site_packages"]) not in sys.path:
        sys.path.insert(0, str(vp["site_packages"]))

    return {
        "venv_dir": venv_dir,
        "browsers_dir": Path(env["PLAYWRIGHT_BROWSERS_PATH"]),
        "debug_dir": temp_root / "debug",
        "temp_root": temp_root,
    }


def launch_reaper_later(target_dir: Path):
    """
    Launch a tiny background process that removes target_dir after this
    process exits. Retries for a while to handle Windows file locks.
    """
    if KEEP_FILES:
        return
    py = sys.executable
    code = r"""
import os, shutil, sys, time, stat
from pathlib import Path

def onerror(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def rm_tree(p: Path, attempts=120):
    for i in range(attempts):
        try:
            if p.exists():
                shutil.rmtree(p, onerror=onerror)
            return
        except Exception:
            time.sleep(0.5)

if __name__ == "__main__":
    p = Path(sys.argv[1])
    time.sleep(1.0)
    rm_tree(p)
"""
    try:
        # Start as detached where possible
        kwargs = {}
        if platform.system().lower().startswith("win"):
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            kwargs["close_fds"] = True
            kwargs["stdin"] = subprocess.DEVNULL
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL
        else:
            kwargs["stdin"] = subprocess.DEVNULL
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL
        subprocess.Popen(
            [py, "-c", code, str(target_dir)],
            **kwargs,
        )
    except Exception:
        # Best-effort; ignore if reaper can't start
        pass


def import_third_party():
    global aiohttp, async_playwright, Browser, BrowserContext, Page, console, box
    try:
        import aiohttp as _aiohttp
        from playwright.async_api import (
            async_playwright as _async_playwright,
            Browser as _Browser,
            BrowserContext as _BrowserContext,
            Page as _Page,
        )
        from rich.console import Console as _Console
        from rich import box as _box

        aiohttp = _aiohttp
        async_playwright = _async_playwright
        Browser = _Browser
        BrowserContext = _BrowserContext
        Page = _Page
        console = _Console()
        box = _box
    except Exception as e:
        print("❌ Failed to import dependencies after bootstrap:", e)
        sys.exit(1)


def debug_log(message: str):
    if DEBUG and console:
        console.print(f"[dim cyan][DEBUG][/dim cyan] {message}")


# ----------------------------- App logic --------------------------------


def format_proxy(proxy: str) -> Optional[str]:
    if not proxy:
        return None
    if proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
        return proxy
    return f"http://{proxy}"


async def fetch_proxies() -> List[str]:
    proxies: List[str] = []
    debug_log("Fetching proxy list from GitHub...")
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in PROXY_LIST_URLS:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        lst = [l.strip() for l in text.split("\n") if l.strip()]
                        proxies.extend(lst)
                        debug_log(f"Fetched {len(lst)} proxies from {url}")
            except Exception as e:
                debug_log(f"Failed to fetch proxies from {url}: {e}")
                continue
    if proxies:
        random.shuffle(proxies)
        debug_log(f"Total proxies available: {len(proxies)}")
    return proxies


class GuerrillaMailClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.email: Optional[str] = None
        self.sid_token: Optional[str] = None
        self.cookies: Optional[Dict[str, str]] = None

    async def get_email_address(self) -> str:
        debug_log("Requesting temporary email from Guerrilla Mail")
        params = {"f": "get_email_address"}
        async with self.session.get(GUERRILLA_MAIL_API, params=params) as r:
            if r.cookies:
                self.cookies = {k: v.value for k, v in r.cookies.items()}
                debug_log(f"Extracted cookies: {self.cookies}")
            data = await r.json()
            self.email = data["email_addr"]
            self.sid_token = data["sid_token"]
            debug_log(f"Email: {self.email}, sid_token: {self.sid_token}")
            return self.email

    async def poll_for_email(self, timeout: int = MAX_EMAIL_WAIT_TIME) -> Optional[str]:
        debug_log(f"Polling email (timeout {timeout}s)")
        params = {"f": "get_email_list", "offset": "0", "sid_token": self.sid_token}
        start = asyncio.get_event_loop().time()
        poll = 0
        while (asyncio.get_event_loop().time() - start) < timeout:
            poll += 1
            kwargs: Dict[str, Any] = {"params": params}
            if self.cookies:
                kwargs["cookies"] = self.cookies
            try:
                async with self.session.get(GUERRILLA_MAIL_API, **kwargs) as r:
                    data = await r.json()
                    emails = data.get("list", [])
                    debug_log(f"Email poll #{poll}: {len(emails)} emails")
                    for em in emails:
                        sender = em.get("mail_from", "").lower()
                        subject = em.get("mail_subject", "")
                        if "ref" in sender or "verify" in subject.lower():
                            mail_id = em["mail_id"]
                            link = await self._fetch_email_body(mail_id)
                            if link:
                                return link
            except Exception as e:
                debug_log(f"Poll error: {e}")
            await asyncio.sleep(EMAIL_CHECK_INTERVAL)
        debug_log("Email polling timed out")
        return None

    async def _fetch_email_body(self, mail_id: str) -> Optional[str]:
        debug_log(f"Fetching email body id={mail_id}")
        params = {"f": "fetch_email", "email_id": mail_id, "sid_token": self.sid_token}
        kwargs: Dict[str, Any] = {"params": params}
        if self.cookies:
            kwargs["cookies"] = self.cookies
        async with self.session.get(GUERRILLA_MAIL_API, **kwargs) as r:
            data = await r.json()
            body = data.get("mail_body", "") or ""
            if DEBUG:
                debug_log(f"Email body preview: {body[:400]}...")
            patterns = [
                r'https?://(?:www\.)?ref\.tools/verify[^\s<>"\']+',
                r'https?://(?:www\.)?ref\.tools/confirm[^\s<>"\']+',
                r'https?://(?:www\.)?ref\.tools/[^\s<>"\']*verify[^\s<>"\']*',
                r'https?://(?:www\.)?ref\.tools/[^\s<>"\']*confirm[^\s<>"\']*',
            ]
            for pat in patterns:
                m = re.search(pat, body)
                if m:
                    return m.group(0)
        return None


class RefToolsAutomation:
    def __init__(self, browser: Browser, debug_dir: Path, proxy: Optional[str] = None):
        self.browser = browser
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.password: str = self._gen_password()
        self.proxy = proxy
        self.debug_dir = debug_dir
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _gen_password(length: int = 16) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def initialize(self):
        context_options: Dict[str, Any] = {
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

    async def signup(self, email: str) -> bool:
        for attempt in range(SIGNUP_MAX_RETRIES):
            try:
                debug_log(f"Signup attempt {attempt + 1}/{SIGNUP_MAX_RETRIES}")
                await self.page.goto(REF_TOOLS_SIGNUP, wait_until="networkidle")
                if DEBUG:
                    p = self.debug_dir / f"debug_signup_{attempt + 1}.png"
                    await self.page.screenshot(path=str(p))
                email_input = self.page.locator('input[type="email"]')
                await email_input.fill(email)
                pwd_input = self.page.locator('input#password[type="password"]')
                await pwd_input.fill(self.password)
                cfm_input = self.page.locator(
                    'input#confirmPassword[type="password"]'
                )
                await cfm_input.fill(self.password)
                btn = self.page.locator('button[type="submit"]')
                await btn.click()
                try:
                    await self.page.wait_for_url("**/dashboard", timeout=15000)
                except Exception as e:
                    debug_log(f"Redirect wait warning: {e}")
                    await asyncio.sleep(3)
                return True
            except Exception as e:
                debug_log(f"Signup error: {e}")
                if attempt < SIGNUP_MAX_RETRIES - 1:
                    if console:
                        console.print(
                            f"[yellow]Signup attempt {attempt + 1} "
                            f"failed, retrying...[/yellow]"
                        )
                    await asyncio.sleep(SIGNUP_RETRY_DELAY)
        if console:
            console.print(
                f"[red]Signup failed after {SIGNUP_MAX_RETRIES} attempts[/red]"
            )
        return False

    async def request_verification_email(self):
        try:
            await asyncio.sleep(2)
            selectors = [
                "button.verify-button",
                ".verification-banner button",
                "button:has-text('Verify')",
                "button:has-text('Send Verification')",
            ]
            for sel in selectors:
                try:
                    btns = self.page.locator(sel)
                    count = await btns.count()
                    if count > 0:
                        await btns.first.wait_for(state="visible", timeout=5000)
                        await btns.first.click()
                        await asyncio.sleep(3)
                        return
                except Exception as e:
                    debug_log(f"Selector '{sel}' error: {e}")
        except Exception as e:
            debug_log(f"Verification button error: {e}")

    async def confirm_email(self, link: str):
        await self.page.goto(link, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)
        if DEBUG:
            p = self.debug_dir / "debug_after_verification.png"
            await self.page.screenshot(path=str(p))

    async def extract_api_key(self) -> Optional[str]:
        try:
            await self.page.goto(REF_TOOLS_KEYS, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            if DEBUG:
                p = self.debug_dir / "debug_keys_page.png"
                await self.page.screenshot(path=str(p))
                html = await self.page.content()
                (self.debug_dir / "debug_keys_page.html").write_text(
                    html, encoding="utf-8"
                )
            selectors = [
                "input[readonly]",
                "input[type='text'][readonly]",
                "textarea[readonly]",
                "code",
                "[data-key]",
                "pre code",
                ".api-key",
                "[class*='key'] code",
            ]
            for sel in selectors:
                try:
                    els = self.page.locator(sel)
                    count = await els.count()
                    for i in range(count):
                        e = els.nth(i)
                        try:
                            val = await e.get_attribute("value")
                            if val and looks_like_key(val):
                                return val.strip()
                        except Exception:
                            pass
                        try:
                            t = (await e.inner_text() or "").strip()
                            if t and looks_like_key(t):
                                return t
                        except Exception:
                            pass
                except Exception as e:
                    debug_log(f"Selector error {sel}: {e}")
            page_text = await self.page.inner_text("body")
            m = re.findall(r"\b[A-Za-z0-9_-]{20,}\b", page_text or "")
            if m:
                return m[0]
        except Exception as e:
            if console:
                console.print(f"[red]Error extracting API key: {e}[/red]")
        return None

    async def close(self):
        if self.context:
            await self.context.close()


def looks_like_key(s: str) -> bool:
    if s.startswith("ref_"):
        return True
    if 30 <= len(s) <= 200 and re.match(r"^[A-Za-z0-9_\-]+$", s):
        bad = [
            "typescript",
            "node.js",
            "error",
            "failed",
            "search",
            "docs",
            "install",
            "verify",
        ]
        return not any(w in s.lower() for w in bad)
    return False


async def run_keygen(temp_dirs: Dict[str, Path]):
    # Imports are ready here
    from rich.panel import Panel
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table

    debug_log("Starting Playwright")
    playwright = await async_playwright().start()

    # Proxy must be set on launch, not on context
    launch_args: Dict[str, Any] = {"headless": not DEBUG}
    current_proxy: Optional[str] = None
    proxies: List[str] = []

    if USE_PROXY:
        if console:
            console.print("[cyan]📡 Fetching fresh proxy list...[/cyan]")
        try:
            proxies = await fetch_proxies()
            if console:
                console.print(
                    f"[green]✓[/green] Loaded [bold]{len(proxies)}[/bold] proxies\n"
                )
            if proxies:
                current_proxy = proxies[0]
        except Exception as e:
            debug_log(f"Proxy fetch failed: {e}")

        if current_proxy:
            fmt = format_proxy(current_proxy)
            if fmt:
                launch_args["proxy"] = {"server": fmt}
                debug_log(f"Using proxy: {fmt}")

    browser: Optional[Browser] = None
    session: Optional[aiohttp.ClientSession] = None
    api_key: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

    try:
        browser = await playwright.chromium.launch(**launch_args)

        # Create HTTP session
        session = aiohttp.ClientSession()

        # Banner
        console.print()
        console.print(
            Panel.fit(
                "[bold bright_cyan]🔑 ref.tools API Key Generator[/bold bright_cyan]\n"
                "[dim]Automated API key generation using temporary email[/dim]",
                border_style="bright_cyan",
                box=box.DOUBLE,
            )
        )
        console.print()
        if DEBUG:
            console.print("[yellow]🐛 DEBUG MODE ENABLED[/yellow]\n")

        # Initialize automation
        ref_tools = RefToolsAutomation(
            browser, debug_dir=temp_dirs["debug_dir"], proxy=current_proxy
        )
        await ref_tools.initialize()

        # Step 1: Get temporary email
        with console.status(
            "[cyan]📧 Generating temporary email...[/cyan]", spinner="dots"
        ):
            guerrilla = GuerrillaMailClient(session)
            email = await guerrilla.get_email_address()
        console.print(
            f"[green]✓[/green] Email generated: [bold cyan]{email}[/bold cyan]"
        )

        # Step 2: Sign up
        with console.status(
            "[cyan]📝 Signing up on ref.tools...[/cyan]", spinner="dots"
        ):
            ok = await ref_tools.signup(email)
        if not ok:
            console.print("[red]✗[/red] Signup failed\n")
            password = ref_tools.password
            return api_key, email, password

        console.print("[green]✓[/green] Signup successful")
        password = ref_tools.password

        # Step 3: Request verification email
        with console.status(
            "[cyan]📬 Requesting verification email...[/cyan]", spinner="dots"
        ):
            await ref_tools.request_verification_email()
        console.print("[green]✓[/green] Verification email requested")

        # Step 4: Wait for verification email
        with console.status(
            "[cyan]⏳ Waiting for verification email (max 2 minutes)...[/cyan]",
            spinner="dots",
        ):
            link = await guerrilla.poll_for_email()
        if not link:
            console.print("[red]✗[/red] Verification email not received\n")
            return api_key, email, password

        console.print("[green]✓[/green] Verification email received")

        # Step 5: Confirm email
        with console.status("[cyan]✉️  Confirming email...[/cyan]", spinner="dots"):
            await ref_tools.confirm_email(link)
        console.print("[green]✓[/green] Email confirmed")

        # Step 6: Extract API key
        with console.status("[cyan]🔐 Extracting API key...[/cyan]", spinner="dots"):
            api_key = await ref_tools.extract_api_key()
        if not api_key:
            console.print("[red]✗[/red] Failed to extract API key\n")
            return api_key, email, password

        # Success output
        console.print()
        console.print("[green]" + "=" * 60 + "[/green]")
        console.print(
            "[bold green]✨ SUCCESS! API Key Generated ✨[/bold green]".center(60)
        )
        console.print("[green]" + "=" * 60 + "[/green]")
        console.print()

        table = Table(
            show_header=False, box=box.ROUNDED, border_style="green", padding=(0, 2)
        )
        table.add_column("Field", style="bold cyan")
        table.add_column("Value", style="bright_white")
        table.add_row("🔑 API Key", f"[bold green]{api_key}[/bold green]")
        table.add_row("📧 Email", email or "")
        table.add_row("🔒 Password", password or "")
        console.print(table)
        console.print()

        console.print(
            Panel(
                "[bold]How to use your API key:[/bold]\n\n"
                "1. Add to your MCP client configuration\n"
                "2. Use in API requests as authentication\n"
                "3. Keep your credentials safe!\n\n"
                "[dim]Visit https://ref.tools/keys to manage your keys[/dim]",
                title="[bold cyan]Next Steps[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        console.print()

        return api_key, email, password
    finally:
        # Tidy resources
        try:
            if session:
                await session.close()
        except Exception:
            pass
        try:
            if browser:
                await browser.close()
        except Exception:
            pass
        try:
            await playwright.stop()
        except Exception:
            pass


def main():
    ensure_python_version()

    # Build temp root and bootstrap env
    temp_root = make_temp_root()
    try:
        env_paths = bootstrap(temp_root)
        import_third_party()

        # Ensure we do not write debug artifacts in user CWD
        os.chdir(temp_root)

        # Run
        api_key, email, password = asyncio.run(run_keygen(env_paths))

        # If failed, print credentials for manual login
        if not api_key and email and password and console:
            console.print("[yellow]Manual access credentials:[/yellow]")
            console.print(f"  Email: {email}")
            console.print(f"  Password: {password}\n")
    finally:
        # Always schedule cleanup unless KEEP_FILES=1
        launch_reaper_later(temp_root)


if __name__ == "__main__":
    main()