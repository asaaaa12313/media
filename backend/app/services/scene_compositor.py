"""씬 전환 + 프레임 시퀀스 생성 (핵심 파이프라인)

멀티 해상도 지원: 1080x1650(기본), 1080x1920, 1080x2560

풀스크린 HTML 렌더링 (우선) → Pillow fallback
사진 전용 씬: HTML/Pillow로 정적 프레임 생성
영상 포함 씬: FFmpeg로 클립 구간 추출 + 오버레이
"""
from __future__ import annotations
import base64
import io
import logging
import shutil
import subprocess
from pathlib import Path
from PIL import Image
logger = logging.getLogger(__name__)

from app.core.config import (
    FPS, TARGET_DURATION,
    SCENE_TIMINGS, TRANSITION_DURATION,
    generate_scene_timings, get_scene_sequence,
)
from app.services.layout_renderer import (
    LayoutRenderer, SceneLayout, build_scene_layout, render_text_overlay_png,
    FRAME_SIZES, DEFAULT_FRAME_SIZE,
)
from app.services.info_panel import render_info_panel
from app.services.brand_system import load_logo, load_logo_small
from app.services.qr_generator import generate_qr
from app.services.image_processor import center_crop_resize
from app.models.schemas import BusinessInfo, BrandConfig, SceneConfig

_jinja_env = None

def _get_jinja_env():
    """Jinja2 환경 lazy 초기화"""
    global _jinja_env
    if _jinja_env is None:
        from jinja2 import Environment, FileSystemLoader
        _jinja_env = Environment(loader=FileSystemLoader("app/templates"))
    return _jinja_env

# 씬 타입 → HTML 템플릿 매핑
_SCENE_HTML_MAP = {
    "intro": "scenes/intro.html",
    "gallery": "scenes/content.html",
    "highlight": "scenes/content.html",
    "review": "scenes/content.html",
    "info_card": "scenes/info_grid.html",
    "feature_list": "scenes/info_grid.html",
    "promotion": "scenes/promo.html",
    "cta": "scenes/ending.html",
}


def _img_to_base64(img: Image.Image | None, fmt: str = "PNG") -> str:
    """PIL Image → base64 문자열"""
    if img is None:
        return ""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()


def _rgb_to_hex(rgb: tuple) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _try_fullscreen_html_render(
    scene: SceneConfig,
    scene_type: str,
    photo: Image.Image | None,
    business: BusinessInfo,
    template: dict,
    logo: Image.Image | None,
    qr: Image.Image | None,
    width: int,
    height: int,
) -> Image.Image | None:
    """씬을 풀스크린 HTML로 렌더링. 실패 시 None → Pillow fallback."""
    tmpl_path = _SCENE_HTML_MAP.get(scene_type)
    if not tmpl_path:
        return None

    try:
        from app.services.html_renderer import render_html_sync

        tmpl = _get_jinja_env().get_template(tmpl_path)

        # 사진을 base64로 변환
        photo_b64 = ""
        if photo:
            photo_b64 = _img_to_base64(photo, "JPEG")

        # 서비스 목록 (info_grid용)
        services = business.services[:6] if business.services else []

        html = tmpl.render(
            width=width, height=height,
            business_name=business.name,
            tagline=business.tagline,
            tagline_sub=business.tagline or "",
            headline=scene.headline or business.name,
            sub_copy=scene.subtext or business.tagline or "",
            highlight=scene.subtext if scene_type in ("highlight", "review") else "",
            photo_base64=photo_b64,
            logo_base64=_img_to_base64(logo),
            qr_base64=_img_to_base64(qr),
            phone=business.phone,
            address=business.address,
            services=services,
            extra_tags=[],
            # promo 전용
            discount="",
            discount_label="",
            cta_text="지금 바로 방문하세요" if scene_type == "cta" else "",
            naver_search=f"네이버에서 '{business.name}' 검색" if scene_type == "promotion" else "",
            # ending 전용
            hours=[],
            # CSS 변수
            primary=_rgb_to_hex(template.get("primary", (50, 50, 50))),
            accent=_rgb_to_hex(template.get("accent", (255, 200, 50))),
            text_color=_rgb_to_hex(template.get("text_on_content", (255, 255, 255))),
            panel_bg=_rgb_to_hex(template.get("panel_bg", (255, 255, 255))),
            text_on_primary=_rgb_to_hex(template.get("text_on_primary", (255, 255, 255))),
        )

        result = render_html_sync(html, width, height)
        if result:
            logger.info(f"[fullscreen_html] {scene_type} → {tmpl_path} 렌더링 성공")
            return result.convert("RGB")
        return None
    except Exception as e:
        logger.warning(f"[fullscreen_html] {scene_type} 렌더링 실패: {e}")
        return None


def _get_scene_at_time(t: float, timings: list[tuple[float, float]] | None = None) -> int:
    timings = timings or SCENE_TIMINGS
    for i, (start, end) in enumerate(timings):
        if start <= t < end:
            return i
    return len(timings) - 1


def _get_transition(t: float, timings: list[tuple[float, float]] | None = None) -> tuple[int, int, float] | None:
    timings = timings or SCENE_TIMINGS
    half = TRANSITION_DURATION / 2
    for i in range(1, len(timings)):
        boundary = timings[i][0]
        if boundary - half <= t < boundary + half:
            progress = (t - (boundary - half)) / TRANSITION_DURATION
            return i - 1, i, min(1.0, max(0.0, progress))
    return None


def _build_scene_layouts(
    business: BusinessInfo,
    scenes: list[SceneConfig],
    template: dict,
) -> list[SceneLayout]:
    """씬 설정 → SceneLayout 리스트 변환"""
    category = business.category
    default_sequence = get_scene_sequence(category, len(scenes))

    layouts = []
    for i, scene in enumerate(scenes):
        # 씬 타입 결정: 사용자 지정 > 업종 기본 시퀀스
        scene_type = scene.scene_type or (default_sequence[i] if i < len(default_sequence) else "cta")

        # 커스텀 텍스트 블록이 있으면 그대로 사용
        custom_blocks = None
        if scene.text_blocks:
            custom_blocks = [tb.model_dump() for tb in scene.text_blocks]

        layout = build_scene_layout(
            scene_type=scene_type,
            template=template,
            headline=scene.headline,
            subtext=scene.subtext,
            business_name=business.name,
            services=business.services,
            custom_blocks=custom_blocks,
            font_color_override=scene.font_color,
            emphasis_color=scene.emphasis_color,
            emphasis_words=scene.emphasis_words,
            layout_variant=getattr(scene, 'layout_variant', 0),
            photo_mode_override=getattr(scene, 'photo_mode', ''),
            photo_overlay_override=getattr(scene, 'photo_overlay', ''),
            text_effect_override=getattr(scene, 'text_effect', ''),
            font_name_override=getattr(scene, 'font_name', ''),
            font_size_scale=getattr(scene, 'font_size_scale', 1.0),
        )
        layouts.append(layout)

    return layouts


def generate_all_frames(
    job_dir: Path,
    business: BusinessInfo,
    brand: BrandConfig,
    scenes: list[SceneConfig],
    photos: list[Image.Image],
    template: dict,
    logo_path: str = "",
    frame_size: str = DEFAULT_FRAME_SIZE,
    progress_cb=None,
) -> str:
    """전체 프레임 시퀀스 생성 (사진 전용 경로)

    Returns: frames 디렉토리 경로
    """
    frames_dir = job_dir / "frames"
    frames_dir.mkdir(exist_ok=True, parents=True)

    # 로고 로드
    logo = load_logo(logo_path) if logo_path else None
    logo_small = load_logo_small(logo_path) if logo_path else None

    # QR 코드 생성
    qr = generate_qr(business.website)

    # LayoutRenderer 초기화 (멀티 해상도)
    renderer = LayoutRenderer(template, logo, business.name, frame_size=frame_size)
    spec = renderer.spec

    # 정보 패널 생성 (1회, 전 씬 동일)
    info_panel = render_info_panel(
        template=template,
        business_name=business.name,
        tagline=business.tagline,
        services=business.services,
        phone=business.phone,
        address=business.address,
        category=business.category,
        logo=logo_small,
        qr=qr,
        panel_height=spec.info_height,
    )
    renderer.set_bottom_bar(info_panel)

    # SceneLayout 빌드
    layouts = _build_scene_layouts(business, scenes, template)
    default_sequence = get_scene_sequence(business.category, len(scenes))

    # 동적 타이밍 생성
    timings = generate_scene_timings(len(scenes))
    total_frames = int(TARGET_DURATION * FPS)

    # 씬별 정적 프레임 프리렌더 (HTML 우선 → Pillow fallback)
    scene_frames: dict[int, Image.Image] = {}
    previews_dir = job_dir / "previews"
    previews_dir.mkdir(exist_ok=True)

    for i, layout in enumerate(layouts):
        if i < len(scenes) and scenes[i].media_type == "photo":
            photo_idx = min(scenes[i].media_index, max(0, len(photos) - 1))
            photo = photos[photo_idx] if photo_idx < len(photos) else (photos[0] if photos else None)

            # HTML 풀스크린 렌더링 시도
            scene_type = scenes[i].scene_type or (default_sequence[i] if i < len(default_sequence) else "cta")
            frame = _try_fullscreen_html_render(
                scenes[i], scene_type, photo, business, template,
                logo_small, qr, spec.width, spec.height,
            )

            # Pillow fallback
            if frame is None:
                frame = renderer.render_scene(layout, photos, photo_idx)

            # 프리뷰 저장
            frame.save(previews_dir / f"scene_{i}.jpg", quality=85)
            scene_frames[i] = frame

    # 씬별 정적 프레임을 파일로 저장 (메모리 해제용)
    scene_frame_paths: dict[int, str] = {}
    for idx, frame in scene_frames.items():
        p = frames_dir / f"scene_base_{idx}.jpg"
        frame.save(p, quality=90)
        scene_frame_paths[idx] = str(p)
        frame.close()
    # 메모리 해제 — 이후 필요 시 디스크에서 읽음
    scene_frames.clear()

    # 사진 원본도 메모리 해제 (이후 디스크 프레임만 사용)
    for p in photos:
        p.close()
    photos.clear()
    import gc; gc.collect()

    # 프레임 시퀀스 생성 (정적 구간은 복사, 전환 구간만 blend)
    import shutil as _shutil
    prev_scene_idx = -1
    prev_path = None

    logger.info(f"[generate_all_frames] scene_frame_paths={list(scene_frame_paths.keys())}, "
                f"total_frames={total_frames}, timings={timings}")
    for k, v in scene_frame_paths.items():
        from pathlib import Path as _P
        p = _P(v)
        logger.info(f"  scene_base_{k}: exists={p.exists()}, size={p.stat().st_size if p.exists() else 0}")

    frames_generated = 0
    for fn in range(total_frames):
        t = fn / FPS
        out_path = frames_dir / f"{fn:05d}.jpg"
        trans = _get_transition(t, timings)

        if trans:
            idx_a, idx_b, progress = trans
            pa = scene_frame_paths.get(idx_a)
            pb = scene_frame_paths.get(idx_b)
            if pa and pb:
                fa = Image.open(pa)
                fb = Image.open(pb)
                blended = Image.blend(fa, fb, progress)
                blended.save(out_path, quality=90)
                fa.close()
                fb.close()
                blended.close()
                frames_generated += 1
            else:
                src = pb or pa
                if src:
                    _shutil.copyfile(src, str(out_path))
                    frames_generated += 1
        else:
            idx = _get_scene_at_time(t, timings)
            src = scene_frame_paths.get(idx)
            if src:
                if idx != prev_scene_idx or prev_path is None:
                    prev_scene_idx = idx
                    prev_path = src
                _shutil.copyfile(src, str(out_path))
                frames_generated += 1

        if progress_cb and fn % FPS == 0:
            progress_cb(fn / total_frames)

    logger.info(f"[generate_all_frames] frames_generated={frames_generated}/{total_frames}")
    # 검증: 첫 프레임 파일 존재 확인
    first_frame = frames_dir / "00000.jpg"
    logger.info(f"  first_frame exists={first_frame.exists()}, "
                f"size={first_frame.stat().st_size if first_frame.exists() else 0}")

    if progress_cb:
        progress_cb(1.0)

    return str(frames_dir)


def generate_mixed_video(
    job_dir: Path,
    business: BusinessInfo,
    brand: BrandConfig,
    scenes: list[SceneConfig],
    photos: list[Image.Image],
    video_paths: dict[int, str],
    template: dict,
    logo_path: str = "",
    frame_size: str = DEFAULT_FRAME_SIZE,
    progress_cb=None,
) -> str:
    """사진 + 영상 혼합 씬 생성

    영상 씬: FFmpeg로 구간 추출 + 텍스트 오버레이 PNG 합성
    사진 씬: Pillow 정적 프레임 → FFmpeg 연결

    Returns: 합성된 무음 영상 경로
    """
    spec = FRAME_SIZES.get(frame_size, FRAME_SIZES[DEFAULT_FRAME_SIZE])
    W, H = spec.width, spec.height

    clips_dir = job_dir / "clips"
    clips_dir.mkdir(exist_ok=True, parents=True)
    previews_dir = job_dir / "previews"
    previews_dir.mkdir(exist_ok=True)

    # 로고/QR/렌더러
    logo = load_logo(logo_path) if logo_path else None
    logo_small = load_logo_small(logo_path) if logo_path else None
    qr = generate_qr(business.website)
    renderer = LayoutRenderer(template, logo, business.name, frame_size=frame_size)
    spec = renderer.spec
    info_panel = render_info_panel(
        template=template,
        business_name=business.name,
        tagline=business.tagline,
        services=business.services,
        phone=business.phone,
        address=business.address,
        category=business.category,
        logo=logo_small,
        qr=qr,
        panel_height=spec.info_height,
    )
    renderer.set_bottom_bar(info_panel)

    layouts = _build_scene_layouts(business, scenes, template)
    default_sequence = get_scene_sequence(business.category, len(scenes))
    timings = generate_scene_timings(len(scenes))
    clip_paths = []

    # Phase 1: 씬 이미지 렌더링 + 디스크 저장
    scene_render_info: list[dict] = []
    for i, (layout, scene) in enumerate(zip(layouts, scenes)):
        start, end = timings[i] if i < len(timings) else (0, 3)
        duration = end - start

        if scene.media_type == "video" and i in video_paths:
            # 영상 씬: 오버레이/바 이미지 저장
            overlay_png = render_text_overlay_png(
                scene.headline, scene.subtext, template, frame_size=frame_size,
            )
            overlay_path = clips_dir / f"overlay_{i}.png"
            overlay_png.save(str(overlay_path))
            overlay_png.close()

            bar_path = clips_dir / f"bar_{i}.png"
            info_panel.save(str(bar_path))

            scene_render_info.append({
                "type": "video", "idx": i, "duration": duration,
                "overlay_path": str(overlay_path), "bar_path": str(bar_path),
            })
        else:
            # 사진 씬: HTML 풀스크린 우선 → Pillow fallback
            photo_idx = min(scene.media_index, max(0, len(photos) - 1))
            photo = photos[photo_idx] if photo_idx < len(photos) else (photos[0] if photos else None)

            scene_type = scene.scene_type or (default_sequence[i] if i < len(default_sequence) else "cta")
            frame = _try_fullscreen_html_render(
                scene, scene_type, photo, business, template,
                logo_small, qr, W, H,
            )
            if frame is None:
                frame = renderer.render_scene(layout, photos, photo_idx)

            frame.save(previews_dir / f"scene_{i}.jpg", quality=85)

            frame_path = clips_dir / f"still_{i}.png"
            frame.save(str(frame_path))
            logger.info(f"[mixed_video] scene_{i}: frame_size={frame.size}, saved={frame_path}")
            frame.close()

            scene_render_info.append({
                "type": "photo", "idx": i, "duration": duration,
                "frame_path": str(frame_path),
            })

    # Phase 2: 메모리 해제 (Pillow 객체 모두 정리 → FFmpeg에 메모리 확보)
    for p in photos:
        p.close()
    photos.clear()
    if logo:
        logo.close()
    if logo_small:
        logo_small.close()
    if info_panel:
        info_panel.close()
    renderer = None
    import gc; gc.collect()
    logger.info("[mixed_video] memory released, starting FFmpeg encoding")

    # Phase 3: FFmpeg 인코딩 (메모리 확보된 상태에서)
    for info in scene_render_info:
        i = info["idx"]
        duration = info["duration"]
        clip_path = clips_dir / f"clip_{i}.mp4"

        if info["type"] == "video":
            _ffmpeg_extract_with_overlay(
                video_paths[i], str(clip_path),
                info["overlay_path"], info["bar_path"],
                W, H, spec.content_height, duration, FPS,
            )
            clip_paths.append(str(clip_path))
            _save_video_preview(str(clip_path), previews_dir / f"scene_{i}.jpg")
        else:
            _ffmpeg_still_to_clip(info["frame_path"], str(clip_path),
                                  W, H, duration, FPS)
            clip_paths.append(str(clip_path))

        if progress_cb:
            progress_cb((i + 1) / len(scenes) * 0.9)

    # 클립 연결
    output_path = str(job_dir / "combined.mp4")
    _ffmpeg_concat_clips(clip_paths, output_path, clips_dir)

    if progress_cb:
        progress_cb(1.0)

    return output_path


# ─────────────────────────────────────────────
# FFmpeg 유틸
# ─────────────────────────────────────────────

def _ffmpeg_extract_with_overlay(
    video_in: str, video_out: str,
    overlay_path: str, bar_path: str,
    width: int, _height: int, content_h: int,
    duration: float, fps: int,
):
    """영상에서 구간 추출 + 크롭/리사이즈 + 텍스트 오버레이 + 하단 바 합성"""
    cmd = [
        "ffmpeg", "-y", "-i", video_in,
        "-i", overlay_path, "-i", bar_path,
        "-filter_complex",
        f"[0:v]scale={width}:{content_h}:force_original_aspect_ratio=increase,"
        f"crop={width}:{content_h},setsar=1[bg];"
        f"[bg][1:v]overlay=0:0[with_text];"
        f"[with_text][2:v]overlay=0:{content_h}[out]",
        "-map", "[out]", "-an",
        "-t", str(duration),
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-threads", "2", "-x264-params", "threads=2:lookahead_threads=1",
        video_out,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error(f"[extract_with_overlay] FFmpeg FULL stderr:\n{result.stderr}")
        raise RuntimeError(f"extract_with_overlay 실패 (rc={result.returncode}): {result.stderr[-500:]}")


def _ffmpeg_still_to_clip(
    image_path: str, video_out: str,
    width: int, height: int,
    duration: float, fps: int,
):
    """정지 이미지 → 영상 클립 변환"""
    # 입력 파일 검증
    from pathlib import Path as _P
    img_p = _P(image_path)
    if not img_p.exists():
        raise RuntimeError(f"still_to_clip: 입력 파일 없음 {image_path}")
    logger.info(f"[still_to_clip] {image_path} (size={img_p.stat().st_size}) → {video_out} ({duration}s, {width}x{height})")

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-t", str(duration),
        "-r", str(fps),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-threads", "2", "-x264-params", "threads=2:lookahead_threads=1",
        "-pix_fmt", "yuv420p",
        video_out,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        # 전체 stderr를 로그에 기록 (Railway 로그에서 확인용)
        logger.error(f"[still_to_clip] FFmpeg FULL stderr:\n{result.stderr}")
        # 에러 메시지: 끝부분에 실제 원인이 있음
        raise RuntimeError(f"still_to_clip 실패 (rc={result.returncode}): {result.stderr[-500:]}")


def _ffmpeg_concat_clips(clip_paths: list[str], output_path: str, work_dir: Path):
    """클립 리스트를 순서대로 연결"""
    list_file = work_dir / "concat.txt"
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    logger.info(f"[concat_clips] {len(clip_paths)} clips → {output_path}")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error(f"[concat_clips] FFmpeg FULL stderr:\n{result.stderr}")
        raise RuntimeError(f"concat_clips 실패 (rc={result.returncode}): {result.stderr[-500:]}")


def _save_video_preview(video_path: str, output_path: Path):
    """영상 첫 프레임을 프리뷰 이미지로 저장"""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-frames:v", "1", "-q:v", "2",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)
