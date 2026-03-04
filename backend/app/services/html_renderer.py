"""HTML → PNG 렌더링 서비스 (Playwright Chromium)

싱글턴 브라우저 인스턴스로 HTML을 PNG 이미지로 변환.
실패 시 None 반환 → 호출자가 Pillow fallback 처리.
"""
from __future__ import annotations
import asyncio
import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

_browser = None
_playwright = None


async def _get_browser():
    """싱글턴 Chromium 브라우저 인스턴스"""
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--single-process",
            ]
        )
    return _browser


async def render_html_to_image(html: str, width: int, height: int) -> Image.Image:
    """HTML 문자열 → PIL Image 변환"""
    browser = await _get_browser()
    page = await browser.new_page(viewport={"width": width, "height": height})
    try:
        await page.set_content(html, wait_until="load")
        await page.wait_for_timeout(200)  # 폰트 로딩 대기
        png_bytes = await page.screenshot(type="png")
        return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    finally:
        await page.close()


def render_html_sync(html: str, width: int, height: int) -> Image.Image | None:
    """동기 래퍼 (기존 Pillow 파이프라인 호환)

    Returns: PIL Image 또는 None (실패 시 → Pillow fallback)
    """
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(render_html_to_image(html, width, height))
        loop.close()
        return result
    except Exception as e:
        logger.warning(f"HTML 렌더링 실패, Pillow fallback: {e}")
        return None
