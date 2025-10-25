#!/usr/bin/env python3
"""
ref.tools API Key Generator
An automated tool for generating API keys from ref.tools using temporary email addresses.

Run directly without cloning:
    curl -sSL https://raw.githubusercontent.com/yourusername/ref-tools-keygen/main/get_ref_key.py | python3 -

Or download and run:
    curl -O https://raw.githubusercontent.com/yourusername/ref-tools-keygen/main/get_ref_key.py
    python3 get_ref_key.py

First time setup:
    pip install playwright aiohttp rich && playwright install chromium
"""

import asyncio
import os
import re
import secrets
import string
import random
import sys
from typing import Optional, Dict, Any, List

try:
    import aiohttp
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich import box
except ImportError as e:
    print("\n⚠️  Missing dependencies. Please install them first:\n")
    print("    pip install playwright aiohttp rich")
    print("    playwright install chromium")
    print("\nOr with uv (faster):")
    print("    pip install uv")
    print("    uv pip install playwright aiohttp rich")
    print("    playwright install chromium\n")
    sys.exit(1)

# Initialize Rich console
console = Console()

# Debug mode - set via environment variable or command line
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
USE_PROXY = os.environ.get("USE_PROXY", "").lower() in ("1", "true", "yes")

# Constants
GUERRILLA_MAIL_API = "https://api.guerrillamail.com/ajax.php"
REF_TOOLS_SIGNUP = "https://ref.tools/signup"
REF_TOOLS_DASHBOARD = "https://ref.tools/dashboard"
REF_TOOLS_KEYS = "https://ref.tools/keys"
EMAIL_CHECK_INTERVAL = 3  # seconds
MAX_EMAIL_WAIT_TIME = 120  # seconds
SIGNUP_MAX_RETRIES = 3
SIGNUP_RETRY_DELAY = 5  # seconds
PROXY_LIST_URLS = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
]
MAX_PROXY_RETRIES = 5


def debug_log(message: str):
    """Log debug messages if DEBUG mode is enabled."""
    if DEBUG:
        console.print(f"[dim cyan][DEBUG][/dim cyan] {message}")


async def fetch_proxies() -> List[str]:
    """
    Fetch fresh proxy list from GitHub.
    
    Returns:
        List of proxy URLs
    """
    proxies = []
    debug_log("Fetching proxy list from GitHub...")
    
    async with aiohttp.ClientSession() as session:
        for url in PROXY_LIST_URLS:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        text = await response.text()
                        proxy_list = [line.strip() for line in text.split('\n') if line.strip()]
                        proxies.extend(proxy_list)
                        debug_log(f"Fetched {len(proxy_list)} proxies from {url}")
            except Exception as e:
                debug_log(f"Failed to fetch proxies from {url}: {e}")
                continue
    
    if proxies:
        random.shuffle(proxies)
        debug_log(f"Total proxies available: {len(proxies)}")
    
    return proxies


def format_proxy(proxy: str) -> Optional[str]:
    """
    Format proxy string to proper URL format.
    
    Args:
        proxy: Proxy in format "ip:port" or "protocol://ip:port"
        
    Returns:
        Formatted proxy URL or None if invalid
    """
    if not proxy:
        return None
    
    # If already has protocol, return as is
    if proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
        return proxy
    
    # Otherwise, assume HTTP
    return f"http://{proxy}"


class GuerrillaMailClient:
    """Asynchronous client for Guerrilla Mail temporary email service."""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.email: Optional[str] = None
        self.sid_token: Optional[str] = None
        self.cookies: Optional[Dict[str, str]] = None

    async def get_email_address(self) -> str:
        """
        Obtain a temporary email address from Guerrilla Mail.
        Extracts and stores session cookies for subsequent requests.
        """
        debug_log("Requesting temporary email from Guerrilla Mail API")
        params = {"f": "get_email_address"}
        async with self.session.get(GUERRILLA_MAIL_API, params=params) as response:
            # Extract PHPSESSID cookie for session management
            if response.cookies:
                self.cookies = {k: v.value for k, v in response.cookies.items()}
                debug_log(f"Extracted cookies: {self.cookies}")

            data = await response.json()
            self.email = data["email_addr"]
            self.sid_token = data["sid_token"]
            debug_log(f"Received email: {self.email}, sid_token: {self.sid_token}")
            return self.email

    async def poll_for_email(self, timeout: int = MAX_EMAIL_WAIT_TIME) -> Optional[str]:
        """
        Poll for emails from ref.tools and extract the verification link.
        
        Args:
            timeout: Maximum time to wait for email (seconds)
            
        Returns:
            Verification link URL or None if not found
        """
        debug_log(f"Starting email polling with timeout: {timeout}s")
        params = {
            "f": "get_email_list",
            "offset": "0",
            "sid_token": self.sid_token,
        }

        start_time = asyncio.get_event_loop().time()
        poll_count = 0

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            poll_count += 1
            debug_log(f"Email poll attempt #{poll_count}")
            
            # Add cookies to request if available
            kwargs = {"params": params}
            if self.cookies:
                kwargs["cookies"] = self.cookies

            async with self.session.get(GUERRILLA_MAIL_API, **kwargs) as response:
                data = await response.json()
                email_list = data.get("list", [])
                debug_log(f"Received {len(email_list)} emails")

                # Check for emails from ref.tools
                for email in email_list:
                    sender = email.get("mail_from", "").lower()
                    subject = email.get("mail_subject", "")
                    debug_log(f"Email from: {sender}, subject: {subject}")
                    
                    if "ref" in sender or "verify" in subject.lower():
                        debug_log(f"Found ref.tools email! mail_id: {email['mail_id']}")
                        mail_id = email["mail_id"]
                        verification_link = await self._fetch_email_body(mail_id)
                        if verification_link:
                            debug_log(f"Extracted verification link: {verification_link}")
                            return verification_link

            await asyncio.sleep(EMAIL_CHECK_INTERVAL)

        debug_log("Email polling timed out")
        return None

    async def _fetch_email_body(self, mail_id: str) -> Optional[str]:
        """
        Fetch the email body and extract the verification link.
        
        Args:
            mail_id: ID of the email to fetch
            
        Returns:
            Verification link or None
        """
        debug_log(f"Fetching email body for mail_id: {mail_id}")
        params = {
            "f": "fetch_email",
            "email_id": mail_id,
            "sid_token": self.sid_token,
        }

        kwargs = {"params": params}
        if self.cookies:
            kwargs["cookies"] = self.cookies

        async with self.session.get(GUERRILLA_MAIL_API, **kwargs) as response:
            data = await response.json()
            body = data.get("mail_body", "")
            debug_log(f"Email body length: {len(body)} characters")
            
            if DEBUG:
                debug_log(f"Email body preview: {body[:500]}...")

            # Extract verification link using regex
            # Look for ref.tools verification or confirm URLs
            patterns = [
                r'https?://(?:www\.)?ref\.tools/verify[^\s<>"\']+',
                r'https?://(?:www\.)?ref\.tools/confirm[^\s<>"\']+',
                r'https?://(?:www\.)?ref\.tools/[^\s<>"\']*verify[^\s<>"\']*',
                r'https?://(?:www\.)?ref\.tools/[^\s<>"\']*confirm[^\s<>"\']*',
            ]

            for pattern in patterns:
                match = re.search(pattern, body)
                if match:
                    debug_log(f"Matched pattern: {pattern}")
                    return match.group(0)

            debug_log("No verification link found in email body")

        return None


class RefToolsAutomation:
    """Asynchronous browser automation for ref.tools signup and key extraction."""

    def __init__(self, browser: Browser, proxy: Optional[str] = None):
        self.browser = browser
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.password: str = self._generate_password()
        self.proxy = proxy

    @staticmethod
    def _generate_password(length: int = 16) -> str:
        """Generate a cryptographically secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def initialize(self):
        """Create a new browser context and page with optional proxy."""
        context_options = {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        if self.proxy:
            formatted_proxy = format_proxy(self.proxy)
            if formatted_proxy:
                context_options["proxy"] = {"server": formatted_proxy}
                debug_log(f"Using proxy: {formatted_proxy}")
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

    async def signup(self, email: str) -> bool:
        """
        Perform signup on ref.tools with retry logic.
        
        Args:
            email: Email address to use for signup
            
        Returns:
            True if signup was successful, False otherwise
        """
        for attempt in range(SIGNUP_MAX_RETRIES):
            try:
                debug_log(f"Signup attempt {attempt + 1}/{SIGNUP_MAX_RETRIES}")
                debug_log(f"Navigating to {REF_TOOLS_SIGNUP}")
                await self.page.goto(REF_TOOLS_SIGNUP, wait_until="networkidle")
                
                if DEBUG:
                    # Take screenshot in debug mode
                    await self.page.screenshot(path=f"debug_signup_{attempt + 1}.png")
                    debug_log(f"Screenshot saved: debug_signup_{attempt + 1}.png")

                # Locate and fill email input
                debug_log("Locating email input field")
                email_input = self.page.locator('input[type="email"]')
                await email_input.fill(email)
                debug_log(f"Filled email: {email}")

                # Locate and fill password input - use ID for specificity
                debug_log("Locating password input field")
                password_input = self.page.locator('input#password[type="password"]')
                await password_input.fill(self.password)
                debug_log("Filled password field")

                # Locate and fill confirm password input
                debug_log("Locating confirm password input field")
                confirm_password_input = self.page.locator('input#confirmPassword[type="password"]')
                await confirm_password_input.fill(self.password)
                debug_log("Filled confirm password field")

                # Click signup button
                debug_log("Locating and clicking signup button")
                signup_button = self.page.locator('button[type="submit"]')
                await signup_button.click()
                debug_log("Signup button clicked")

                # Wait for navigation to dashboard (no email verification needed)
                debug_log("Waiting for redirect to dashboard...")
                try:
                    # Wait for URL to change to dashboard page
                    await self.page.wait_for_url("**/dashboard", timeout=10000)
                    debug_log("Successfully redirected to dashboard")
                except Exception as e:
                    debug_log(f"Redirect wait error (continuing anyway): {e}")
                    await asyncio.sleep(3)  # Fallback wait
                
                debug_log("Signup form submitted successfully")
                return True

            except Exception as e:
                debug_log(f"Signup attempt {attempt + 1} error: {str(e)}")
                if attempt < SIGNUP_MAX_RETRIES - 1:
                    console.print(
                        f"[yellow]Signup attempt {attempt + 1} failed, retrying...[/yellow]"
                    )
                    await asyncio.sleep(SIGNUP_RETRY_DELAY)
                else:
                    console.print(f"[red]Signup failed after {SIGNUP_MAX_RETRIES} attempts: {e}[/red]")
                    return False

        return False

    async def request_verification_email(self):
        """Click the 'Send Verification Email' button on the dashboard."""
        try:
            debug_log("Looking for verification email button")
            
            # Wait a bit for the page to fully render
            await asyncio.sleep(2)
            
            # Look for the "Send Verification Email" button using multiple selectors
            selectors = [
                "button.verify-button",
                ".verification-banner button",
                "button.verify-button",
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    verify_button = self.page.locator(selector)
                    count = await verify_button.count()
                    debug_log(f"Selector '{selector}' found {count} buttons")
                    
                    if count > 0:
                        # Wait for the button to be visible and clickable
                        await verify_button.first.wait_for(state="visible", timeout=5000)
                        await verify_button.first.click()
                        debug_log(f"✓ Clicked 'Send Verification Email' button using selector: {selector}")
                        await asyncio.sleep(3)  # Wait for the email to be sent
                        clicked = True
                        break
                except Exception as e:
                    debug_log(f"Error with selector '{selector}': {e}")
                    continue
            
            if not clicked:
                debug_log("WARNING: No verification button found - email may already be verified or button not loaded")
                
        except Exception as e:
            debug_log(f"Error requesting verification email: {e}")
            # Don't fail here - continue anyway

    async def confirm_email(self, verification_link: str):
        """
        Navigate to the email verification link.
        
        Args:
            verification_link: URL to verify the email
        """
        debug_log(f"Navigating to verification link: {verification_link}")
        await self.page.goto(verification_link, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)  # Allow time for processing and redirect
        debug_log("Email confirmation completed")
        
        if DEBUG:
            await self.page.screenshot(path="debug_after_verification.png")
            debug_log("Screenshot saved: debug_after_verification.png")

    async def extract_api_key(self) -> Optional[str]:
        """
        Navigate to the keys page and extract the API key.
        
        Returns:
            The API key or None if not found
        """
        try:
            # Navigate to the keys page
            debug_log(f"Navigating to {REF_TOOLS_KEYS}")
            await self.page.goto(REF_TOOLS_KEYS, wait_until="domcontentloaded", timeout=15000)
            
            # Wait for page to be fully loaded
            await asyncio.sleep(3)
            
            if DEBUG:
                await self.page.screenshot(path="debug_keys_page.png")
                debug_log("Screenshot saved: debug_keys_page.png")
                # Also save the HTML for inspection
                html_content = await self.page.content()
                with open("debug_keys_page.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                debug_log("HTML saved: debug_keys_page.html")

            # Try multiple selectors to find the API key
            # Look for elements that specifically contain API key patterns
            selectors = [
                # Look for input fields with readonly attribute (common for API keys)
                "input[readonly]",
                "input[type='text'][readonly]",
                # Look for code elements that contain long alphanumeric strings
                "code",
                # Other possibilities
                "[data-key]",
                "pre code",
                ".api-key",
                "[class*='key'] code",
                "textarea[readonly]",
            ]

            # First pass: try to find elements with API key-like content
            for selector in selectors:
                try:
                    debug_log(f"Trying selector: {selector}")
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    debug_log(f"Found {count} elements for selector: {selector}")
                    
                    # Check each element
                    for i in range(count):
                        element = elements.nth(i)
                        
                        # Try to get the value attribute first (for inputs/textareas)
                        try:
                            api_key = await element.get_attribute("value")
                            if api_key:
                                debug_log(f"Element {i} value attribute: {api_key[:50]}...")
                                # Check if it looks like an API key (starts with ref_ or is long alphanumeric)
                                if (api_key.startswith("ref_") or len(api_key) > 30) and len(api_key) < 200:
                                    debug_log(f"Valid API key found in value attribute!")
                                    return api_key.strip()
                        except:
                            pass
                        
                        # Try inner text
                        try:
                            api_key = await element.inner_text()
                            if api_key:
                                api_key = api_key.strip()
                                debug_log(f"Element {i} inner text: {api_key[:50]}...")
                                # Check if it looks like an API key
                                if api_key.startswith("ref_") or (len(api_key) > 30 and len(api_key) < 200):
                                    # Make sure it's not just random text
                                    if not any(word in api_key.lower() for word in ["typescript", "node.js", "error", "failed", "search", "docs", "install", "verify"]):
                                        debug_log(f"Valid API key found in text content!")
                                        return api_key
                        except:
                            pass
                            
                except Exception as e:
                    debug_log(f"Error with selector {selector}: {e}")
                    continue

            # If no key found with selectors, try extracting from page text
            debug_log("Attempting to extract API key from page text")
            page_text = await self.page.inner_text("body")
            if DEBUG:
                debug_log(f"Page text preview: {page_text[:500]}...")
            
            # Look for patterns that might be API keys (alphanumeric strings of reasonable length)
            key_pattern = r'\b[A-Za-z0-9_-]{20,}\b'
            matches = re.findall(key_pattern, page_text)
            debug_log(f"Found {len(matches)} potential API key patterns")
            if matches:
                debug_log(f"Using first match: {matches[0]}")
                return matches[0]

        except Exception as e:
            console.print(f"[red]Error extracting API key: {e}[/red]")
            debug_log(f"Exception details: {e}")

        return None

    async def close(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()


async def main():
    """Main execution flow for ref.tools API key generation."""
    # Display banner
    console.print()
    console.print(Panel.fit(
        "[bold bright_cyan]🔑 ref.tools API Key Generator[/bold bright_cyan]\n"
        "[dim]Automated API key generation using temporary email[/dim]",
        border_style="bright_cyan",
        box=box.DOUBLE
    ))
    console.print()
    
    if DEBUG:
        console.print("[yellow]🐛 DEBUG MODE ENABLED[/yellow]\n")

    browser: Optional[Browser] = None
    session: Optional[aiohttp.ClientSession] = None
    proxies: List[str] = []
    current_proxy: Optional[str] = None
    proxy_attempt = 0

    try:
        # Fetch proxies only if enabled
        if USE_PROXY:
            with console.status("[cyan]📡 Fetching fresh proxy list...[/cyan]", spinner="dots") as status:
                proxies = await fetch_proxies()
            
            if proxies:
                console.print(f"[green]✓[/green] Loaded [bold]{len(proxies)}[/bold] proxies\n")
                current_proxy = proxies[proxy_attempt] if proxy_attempt < len(proxies) else None
            else:
                console.print("[yellow]⚠[/yellow] No proxies loaded, continuing without proxy\n")
        else:
            debug_log("Proxy mode disabled, running without proxy")
        
        # Initialize with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Initializing browser...", total=None)
            # Select proxy if available
            if proxies and proxy_attempt < len(proxies):
                current_proxy = proxies[proxy_attempt]
                debug_log(f"Attempting with proxy #{proxy_attempt + 1}")
            
            # Launch browser
            debug_log("Starting Playwright")
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=not DEBUG)
            debug_log(f"Browser launched (headless={not DEBUG})")

            # Create HTTP session
            session = aiohttp.ClientSession()

            # Initialize clients
            guerrilla = GuerrillaMailClient(session)
            ref_tools = RefToolsAutomation(browser, proxy=current_proxy)
            await ref_tools.initialize()
            
            progress.update(task, description="[cyan]Browser ready")

        # Step 1: Get temporary email
        with console.status("[cyan]📧 Generating temporary email...[/cyan]", spinner="dots"):
            email = await guerrilla.get_email_address()
        console.print(f"[green]✓[/green] Email generated: [bold cyan]{email}[/bold cyan]")

        # Step 2: Sign up on ref.tools
        with console.status(f"[cyan]📝 Signing up on ref.tools...[/cyan]", spinner="dots"):
            signup_success = await ref_tools.signup(email)

        if not signup_success:
            console.print("[red]✗[/red] Signup failed\n")
            return

        console.print("[green]✓[/green] Signup successful")

        # Step 3: Request verification email
        with console.status("[cyan]📬 Requesting verification email...[/cyan]", spinner="dots"):
            await ref_tools.request_verification_email()
        console.print("[green]✓[/green] Verification email requested")

        # Step 4: Wait for verification email
        with console.status("[cyan]⏳ Waiting for verification email (max 2 minutes)...[/cyan]", spinner="dots"):
            verification_link = await guerrilla.poll_for_email()

        if not verification_link:
            console.print("[red]✗[/red] Verification email not received\n")
            return

        console.print("[green]✓[/green] Verification email received")

        # Step 5: Confirm email
        with console.status("[cyan]✉️  Confirming email...[/cyan]", spinner="dots"):
            await ref_tools.confirm_email(verification_link)
        console.print("[green]✓[/green] Email confirmed")

        # Step 6: Extract API key
        with console.status("[cyan]🔐 Extracting API key...[/cyan]", spinner="dots"):
            api_key = await ref_tools.extract_api_key()

        if not api_key:
            console.print("[red]✗[/red] Failed to extract API key\n")
            console.print("[yellow]Manual access credentials:[/yellow]")
            console.print(f"  Email: {email}")
            console.print(f"  Password: {ref_tools.password}\n")
            return

        # Display success with beautiful output
        console.print()
        console.print("[green]" + "="*60 + "[/green]")
        console.print("[bold green]✨ SUCCESS! API Key Generated ✨[/bold green]".center(60))
        console.print("[green]" + "="*60 + "[/green]")
        console.print()
        
        # Create results table
        table = Table(show_header=False, box=box.ROUNDED, border_style="green", padding=(0, 2))
        table.add_column("Field", style="bold cyan")
        table.add_column("Value", style="bright_white")
        
        table.add_row("🔑 API Key", f"[bold green]{api_key}[/bold green]")
        table.add_row("📧 Email", email)
        table.add_row("🔒 Password", ref_tools.password)
        
        console.print(table)
        console.print()
        
        # Instructions
        console.print(Panel(
            "[bold]How to use your API key:[/bold]\n\n"
            "1. Add to your MCP client configuration\n"
            "2. Use in API requests as authentication\n"
            "3. Keep your credentials safe!\n\n"
            "[dim]Visit https://ref.tools/keys to manage your keys[/dim]",
            title="[bold cyan]Next Steps[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        console.print()

    except Exception as e:
        console.print(f"\n[red]✗[/red] An error occurred: [dim]{str(e)}[/dim]\n")
        
        # Retry with different proxy if available
        if proxies and proxy_attempt < MAX_PROXY_RETRIES and proxy_attempt < len(proxies):
            console.print(f"[yellow]⟳[/yellow] Retrying with different proxy ({proxy_attempt + 1}/{MAX_PROXY_RETRIES})...\n")
            await asyncio.sleep(2)
            # Close current browser if exists
            if browser:
                try:
                    await browser.close()
                except:
                    pass
            # Retry without incrementing attempt count yet
            return await main_with_retry(proxy_attempt + 1, proxies)
        
        if DEBUG:
            raise

    finally:
        # Clean up resources
        if session:
            try:
                await session.close()
            except:
                pass
        if browser:
            try:
                await browser.close()
            except:
                pass


async def main_with_retry(proxy_attempt: int = 0, proxies: Optional[List[str]] = None):
    """Main function with retry logic."""
    return await main()


if __name__ == "__main__":
    asyncio.run(main())
