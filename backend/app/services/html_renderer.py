"""HTML → PNG / MP4 렌더링 서비스 (Playwright Chromium)

싱글턴 브라우저 인스턴스로 HTML을 PNG 이미지 또는 MP4 영상으로 변환.
실패 시 None 반환 → 호출자가 Pillow fallback 처리.
"""
from __future__ import annotations
import asyncio
import io
import logging
import subprocess
import tempfile
from pathlib import Path
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


async def render_html_to_video(
    html: str, width: int, height: int,
    duration: float = 3.0, output_path: str = "",
) -> str | None:
    """HTML + CSS animation → MP4 클립 (Playwright video recording)

    Args:
        html: 렌더링할 HTML (CSS animation 포함)
        width, height: 영상 크기
        duration: 녹화 시간 (초)
        output_path: 출력 MP4 경로 (빈 문자열이면 임시 파일)
    Returns:
        MP4 파일 경로 또는 None (실패 시)
    """
    browser = await _get_browser()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # 비디오 녹화 컨텍스트 생성
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=tmp_dir,
            record_video_size={"width": width, "height": height},
        )
        page = await context.new_page()
        try:
            await page.set_content(html, wait_until="load")
            await page.wait_for_timeout(200)  # 폰트 로딩 대기
            # CSS 애니메이션 재생 대기
            await page.wait_for_timeout(int(duration * 1000))
        finally:
            await page.close()
            await context.close()

        # Playwright가 생성한 webm 파일 찾기
        webm_files = list(Path(tmp_dir).glob("*.webm"))
        if not webm_files:
            logger.warning("[render_html_to_video] webm 파일 미생성")
            return None

        webm_path = str(webm_files[0])

        # webm → mp4 변환
        if not output_path:
            output_path = tempfile.mktemp(suffix=".mp4")

        cmd = [
            "ffmpeg", "-y", "-i", webm_path,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            "-an",  # 오디오 없음
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"[render_html_to_video] webm→mp4 변환 실패: {result.stderr[-300:]}")
            return None

        logger.info(f"[render_html_to_video] {width}x{height}, {duration}s → {output_path}")
        return output_path


def render_html_sync(html: str, width: int, height: int) -> Image.Image | None:
    """동기 래퍼 - 스크린샷 (기존 Pillow 파이프라인 호환, 프리뷰용)

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


def render_html_to_video_sync(
    html: str, width: int, height: int,
    duration: float = 3.0, output_path: str = "",
) -> str | None:
    """동기 래퍼 - 영상 녹화

    Returns: MP4 파일 경로 또는 None (실패 시)
    """
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            render_html_to_video(html, width, height, duration, output_path)
        )
        loop.close()
        return result
    except Exception as e:
        logger.warning(f"HTML 영상 렌더링 실패: {e}")
        return None
