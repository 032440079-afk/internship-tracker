"""
Ilan sayfasini acip gorunur metnini (is tanimi) dondurur. Tek bir tarayici tum calisma boyunca paylasilir.
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

MAX_CHARS = 8000


class JobPageReader:
    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def read(self, url: str, timeout_ms: int = 25000) -> str:
        page = self._browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ))
        try:
            try:
                page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            except PlaywrightTimeout:
                pass
            return page.inner_text("body")[:MAX_CHARS]
        finally:
            page.close()
