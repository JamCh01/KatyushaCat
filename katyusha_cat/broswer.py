import pyppeteer
import asyncio


class Browser:
    def __init__(self):
        self.args = [
            "--no-sandbox",
            "--allow-insecure-localhost",
            "--ignore-certificate-errors",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-xss-auditor",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--allow-running-insecure-content",
            "--disable-webgl",
            "--disable-popup-blocking",
            "--enable-features=NetworkService",
            "--enable-automation",
            "--process-per-tab",
            "--allow-running-insecure-content",
            "--no-first-run",
            "--no-startup-window",
        ]

    async def _init_browser(self):
        self.browser = await pyppeteer.launch(
            headless=False, ignoreHTTPSErrors=True, args=self.args, dumpio=True
        )
        return self.browser

    async def _close_browser(self):
        await self.browser.close()


class Page:
    def __init__(self, browser, base_http):
        self.browser = browser
        self.base_http = base_http

    async def _init_page(self):
        page = await self.browser.newPage()
        return page

    async def close_dialog(self, dialog):
        await dialog.dismiss()

    async def _close_page(self, page):
        await page.close()

    async def fetch(self, page):

        try:
            await page.setViewport(viewport={"width": 1920, "height": 4096})
            await page.setUserAgent(
                userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"
            )
            await page.goto(
                url=self.url,
                options={"waitUntil": ["networkidle2"], "timeout": 10 * 1000},
            )
            await asyncio.sleep(10)
            content = await page.content()
        except Exception:
            content = ""
        await self._close_page(page)
        return content
