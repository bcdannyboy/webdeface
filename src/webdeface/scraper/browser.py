"""Playwright browser automation with stealth configuration for web scraping."""

import asyncio
import random
from contextlib import asynccontextmanager
from typing import Optional

from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from ..config import get_settings
from ..utils.logging import get_structured_logger
from .types import ScrapingError

logger = get_structured_logger(__name__)


class StealthBrowser:
    """Playwright browser with stealth configuration and anti-detection measures."""

    def __init__(self):
        self.settings = get_settings().scraping
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self._browser_lock = asyncio.Lock()

    async def setup(self) -> None:
        """Initialize Playwright and browser with stealth configuration."""
        if self.browser:
            return

        async with self._browser_lock:
            if self.browser:
                return

            logger.info("Initializing Playwright browser with stealth configuration")

            self.playwright = await async_playwright().start()

            # Launch browser with stealth options
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-ipc-flooding-protection",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=TranslateUI",
                    "--disable-features=BlinkGenPropertyTrees",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ],
            )

            logger.info("Playwright browser initialized successfully")

    async def cleanup(self) -> None:
        """Clean up browser and Playwright instances."""
        async with self._browser_lock:
            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            logger.info("Playwright browser cleaned up")

    @asynccontextmanager
    async def create_context(self, **context_options):
        """Create a new browser context with stealth configuration."""
        if not self.browser:
            await self.setup()

        # Default stealth context options
        default_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": random.choice(self.settings.user_agents),
            "extra_http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            "java_script_enabled": True,
            "bypass_csp": True,
        }

        # Merge user options with defaults
        options = {**default_options, **context_options}

        context = await self.browser.new_context(**options)

        # Add stealth scripts
        await context.add_init_script(
            """
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });

            // Mock chrome object
            window.chrome = {
                runtime: {},
            };
        """
        )

        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def create_page(
        self, context: Optional[BrowserContext] = None, **page_options
    ):
        """Create a new page with stealth configuration."""
        if context:
            # Use existing context
            page = await context.new_page()
            
            # Set default timeouts
            page.set_default_timeout(self.settings.default_timeout)
            page.set_default_navigation_timeout(self.settings.default_timeout)

            # Random delay to avoid detection
            await asyncio.sleep(random.uniform(0.5, 2.0))

            try:
                yield page
            finally:
                await page.close()
        else:
            # Create our own context
            async with self.create_context() as ctx:
                page = await ctx.new_page()
                
                # Set default timeouts
                page.set_default_timeout(self.settings.default_timeout)
                page.set_default_navigation_timeout(self.settings.default_timeout)

                # Random delay to avoid detection
                await asyncio.sleep(random.uniform(0.5, 2.0))

                try:
                    yield page
                finally:
                    await page.close()


class BrowserPool:
    """Pool of stealth browsers for concurrent scraping."""

    def __init__(self, max_browsers: int = 3):
        self.max_browsers = max_browsers
        self.browsers: list[StealthBrowser] = []
        self.available_browsers: asyncio.Queue = asyncio.Queue()
        self._initialized = False
        self._lock = asyncio.Lock()

    async def setup(self) -> None:
        """Initialize browser pool."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info(f"Initializing browser pool with {self.max_browsers} browsers")

            # Create and initialize browsers
            for i in range(self.max_browsers):
                browser = StealthBrowser()
                await browser.setup()
                self.browsers.append(browser)
                await self.available_browsers.put(browser)

            self._initialized = True
            logger.info("Browser pool initialization complete")

    async def cleanup(self) -> None:
        """Clean up all browsers in the pool."""
        async with self._lock:
            logger.info("Cleaning up browser pool")

            # Clean up all browsers
            for browser in self.browsers:
                await browser.cleanup()

            self.browsers.clear()

            # Clear the queue
            while not self.available_browsers.empty():
                try:
                    self.available_browsers.get_nowait()
                except asyncio.QueueEmpty:
                    break

            self._initialized = False
            logger.info("Browser pool cleanup complete")

    @asynccontextmanager
    async def get_browser(self):
        """Get a browser from the pool."""
        if not self._initialized:
            await self.setup()

        # Get an available browser
        browser = await self.available_browsers.get()

        try:
            yield browser
        finally:
            # Return browser to the pool
            await self.available_browsers.put(browser)


# Global browser pool instance
_browser_pool: Optional[BrowserPool] = None


async def get_browser_pool() -> BrowserPool:
    """Get or create the global browser pool."""
    global _browser_pool

    if _browser_pool is None:
        _browser_pool = BrowserPool()
        await _browser_pool.setup()

    return _browser_pool


async def cleanup_browser_pool() -> None:
    """Clean up the global browser pool."""
    global _browser_pool

    if _browser_pool:
        await _browser_pool.cleanup()
        _browser_pool = None


class BrowserManager:
    """High-level browser management with error handling and retries."""

    def __init__(self):
        self.settings = get_settings().scraping

    async def navigate_with_retries(
        self,
        page: Page,
        url: str,
        wait_for: str = "networkidle",
        max_retries: Optional[int] = None,
    ) -> bool:
        """Navigate to URL with retries and error handling."""
        if max_retries is None:
            max_retries = self.settings.max_retries

        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Navigating to {url} (attempt {attempt + 1})")

                await page.goto(url, wait_until=wait_for)

                # Check if page loaded successfully
                await page.wait_for_load_state("networkidle", timeout=5000)

                logger.debug(f"Successfully navigated to {url}")
                return True

            except PlaywrightTimeoutError as e:
                logger.warning(
                    f"Navigation timeout for {url} (attempt {attempt + 1}): {str(e)}"
                )
                if attempt == max_retries:
                    raise ScrapingError(
                        f"Navigation failed after {max_retries + 1} attempts: {str(e)}"
                    )

                # Random delay before retry
                await asyncio.sleep(random.uniform(1.0, 3.0))

            except Exception as e:
                logger.error(f"Navigation error for {url}: {str(e)}")
                if attempt == max_retries:
                    raise ScrapingError(f"Navigation failed: {str(e)}")

                await asyncio.sleep(random.uniform(1.0, 3.0))

        return False

    async def wait_for_content(
        self,
        page: Page,
        selectors: Optional[list[str]] = None,
        timeout: Optional[int] = None,
    ) -> bool:
        """Wait for page content to load."""
        if timeout is None:
            timeout = self.settings.default_timeout

        default_selectors = ["body", "main", '[role="main"]', ".content", "#content"]
        wait_selectors = selectors or default_selectors

        for selector in wait_selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout)
                logger.debug(f"Found content selector: {selector}")
                return True
            except PlaywrightTimeoutError:
                continue

        # Fallback: wait for any content
        try:
            await page.wait_for_function(
                "document.body && document.body.innerText.length > 0", timeout=timeout
            )
            return True
        except PlaywrightTimeoutError:
            logger.warning(
                "Content loading timeout - proceeding with available content"
            )
            return False

    async def inject_stealth_scripts(self, page: Page) -> None:
        """Inject additional stealth scripts into the page."""
        stealth_script = """
            // Additional stealth measures
            if (navigator.webdriver) {
                delete navigator.webdriver;
            }

            // Mock screen properties
            Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
            Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });

            // Mock battery API
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            }
        """

        try:
            await page.evaluate(stealth_script)
        except Exception as e:
            logger.debug(f"Failed to inject stealth scripts: {str(e)}")
