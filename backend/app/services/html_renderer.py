"""HTML → PNG / MP4 렌더링 서비스 (Playwright Chromium)

싱글턴 브라우저 인스턴스로 HTML을 PNG 이미지 또는 MP4 영상으로 변환.
영상 녹화: 스크린샷 기반 프레임 캡처 → FFmpeg pipe → MP4
실패 시 None 반환 → 호출자가 Pillow fallback 처리.
"""
from __future__ import annotations
import asyncio
import io
import logging
import subprocess
import tempfile
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
    duration: float = 3.0, fps: int = 15, output_path: str = "",
) -> str | None:
    """HTML + CSS animation → MP4 클립 (스크린샷 프레임 캡처 방식)

    Playwright 페이지에서 일정 간격으로 스크린샷을 찍어 FFmpeg로 MP4 생성.
    record_video API 대신 직접 프레임 캡처하여 정확한 duration 보장.

    Args:
        html: 렌더링할 HTML (CSS animation 포함)
        width, height: 영상 크기
        duration: 녹화 시간 (초)
        fps: 프레임레이트 (기본 15fps — 성능과 품질 균형)
        output_path: 출력 MP4 경로 (빈 문자열이면 임시 파일)
    Returns:
        MP4 파일 경로 또는 None (실패 시)
    """
    browser = await _get_browser()
    page = await browser.new_page(viewport={"width": width, "height": height})

    try:
        await page.set_content(html, wait_until="load")
        await page.wait_for_timeout(300)  # 폰트 로딩 대기

        if not output_path:
            output_path = tempfile.mktemp(suffix=".mp4")

        total_frames = int(duration * fps)
        frame_interval_ms = 1000.0 / fps

        # FFmpeg pipe 입력으로 JPEG 프레임 직접 전송
        cmd = [
            "ffmpeg", "-y",
            "-f", "image2pipe", "-framerate", str(fps),
            "-i", "pipe:0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-r", "30",  # 출력은 30fps
            "-pix_fmt", "yuv420p",
            "-an",
            output_path,
        ]
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        for i in range(total_frames):
            jpg_bytes = await page.screenshot(type="jpeg", quality=85)
            proc.stdin.write(jpg_bytes)
            # 다음 프레임까지 대기 (CSS 애니메이션 진행)
            if i < total_frames - 1:
                await page.wait_for_timeout(int(frame_interval_ms))

        proc.stdin.close()
        stdout, stderr = proc.communicate(timeout=60)

        if proc.returncode != 0:
            logger.error(f"[render_html_to_video] FFmpeg 실패: {stderr.decode()[-300:]}")
            return None

        logger.info(f"[render_html_to_video] {width}x{height}, {duration}s, {total_frames}frames → {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"[render_html_to_video] 프레임 캡처 실패: {e}")
        return None
    finally:
        await page.close()


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
            render_html_to_video(html, width, height, duration, 15, output_path)
        )
        loop.close()
        return result
    except Exception as e:
        logger.warning(f"HTML 영상 렌더링 실패: {e}")
        return None
