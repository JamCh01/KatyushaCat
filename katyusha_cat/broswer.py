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
            "--allow-running-insecure-content",
        ]
        self.is_running = False

    async def _init_browser(self):
        self.browser = await pyppeteer.launch(
            headless=False, ignoreHTTPSErrors=True, args=self.args, dumpio=True
        )
        self.is_running = True
        return self.browser

    async def _close_browser(self):
        await self.browser.close()
        self.is_running = False


class Page:
    def __init__(self, browser, base_http):
        self.browser = browser
        self.base_http = base_http

    async def _init_page(self):
        self.page = await self.browser.newPage()

    async def close_dialog(self, dialog):
        await dialog.dismiss()

    async def _close_page(self):
        await self.page.close()

    async def fetch(self):

        try:
            await self.page.setUserAgent(
                userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"
            )
            response = await self.page.goto(
                url=self.base_http.get("url"),
                options={"waitUntil": ["networkidle2"], "timeout": 30 * 1000},
            )
            await asyncio.sleep(10)
        except Exception:
            import traceback

            traceback.print_exc()
            response = None
        return response

