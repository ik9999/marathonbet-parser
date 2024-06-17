import asyncio
from playwright.async_api import async_playwright, BrowserType, Browser
from loguru import logger

class BrowserManager:
    browser: Browser

    @classmethod
    async def create(cls):
        self = cls()
        try:
            async with async_playwright() as p:
                browser_type: BrowserType = p.chromium
                logger.trace("Launching browser")
                self.browser = await browser_type.launch(headless=False)
                logger.trace("Browser launched")
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
