"""씬 전환 + 프레임 시퀀스 생성 (핵심 파이프라인)

멀티 해상도 지원: 1080x1650(기본), 1080x1920, 1080x2560

사진 전용 씬: Pillow로 정적 프레임 생성
영상 포함 씬: FFmpeg로 클립 구간 추출 + 오버레이
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from PIL import Image

from app.core.config import (
    FPS, TARGET_DURATION,
    SCENE_TIMINGS, TRANSITION_DURATION,
    generate_scene_timings, get_scene_sequence,
)
from app.services.layout_renderer import (
    LayoutRenderer, SceneLayout, build_scene_layout, render_text_overlay_png,
    FRAME_SIZES, DEFAULT_FRAME_SIZE,
)
from app.services.info_panel import render_bottom_bar
from app.services.brand_system import load_logo, load_logo_small
from app.services.qr_generator import generate_qr
from app.services.image_processor import center_crop_resize
from app.models.schemas import BusinessInfo, BrandConfig, SceneConfig


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

    # 하단 바 생성 (1회, 전 씬 동일)
    bottom_bar = render_bottom_bar(
        template, business.name, business.phone, business.address,
        logo_small, qr,
    )
    renderer.set_bottom_bar(bottom_bar)

    # SceneLayout 빌드
    layouts = _build_scene_layouts(business, scenes, template)

    # 동적 타이밍 생성
    timings = generate_scene_timings(len(scenes))
    total_frames = int(TARGET_DURATION * FPS)

    # 씬별 정적 프레임 프리렌더
    scene_frames: dict[int, Image.Image] = {}
    previews_dir = job_dir / "previews"
    previews_dir.mkdir(exist_ok=True)

    for i, layout in enumerate(layouts):
        if i < len(scenes) and scenes[i].media_type == "photo":
            photo_idx = min(scenes[i].media_index, max(0, len(photos) - 1))
            frame = renderer.render_scene(layout, photos, photo_idx)
            scene_frames[i] = frame
            # 프리뷰 저장
            frame.save(previews_dir / f"scene_{i}.jpg", quality=85)

    # 프레임 시퀀스 생성 (크로스페이드 포함)
    for fn in range(total_frames):
        t = fn / FPS
        trans = _get_transition(t, timings)

        if trans:
            idx_a, idx_b, progress = trans
            fa = scene_frames.get(idx_a)
            fb = scene_frames.get(idx_b)
            if fa and fb:
                blended = Image.blend(fa, fb, progress)
                blended.save(frames_dir / f"{fn:05d}.jpg", quality=90)
            else:
                (fb or fa).save(frames_dir / f"{fn:05d}.jpg", quality=90)
        else:
            idx = _get_scene_at_time(t, timings)
            frame = scene_frames.get(idx)
            if frame:
                frame.save(frames_dir / f"{fn:05d}.jpg", quality=90)

        if progress_cb and fn % FPS == 0:
            progress_cb(fn / total_frames)

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
    bottom_bar = render_bottom_bar(
        template, business.name, business.phone, business.address,
        logo_small, qr,
    )
    renderer.set_bottom_bar(bottom_bar)

    layouts = _build_scene_layouts(business, scenes, template)
    timings = generate_scene_timings(len(scenes))
    clip_paths = []

    for i, (layout, scene) in enumerate(zip(layouts, scenes)):
        start, end = timings[i] if i < len(timings) else (0, 3)
        duration = end - start

        if scene.media_type == "video" and i in video_paths:
            # 영상 씬: FFmpeg로 구간 추출 + 오버레이
            clip_path = clips_dir / f"clip_{i}.mp4"
            overlay_png = render_text_overlay_png(
                scene.headline, scene.subtext, template, frame_size=frame_size,
            )
            overlay_path = clips_dir / f"overlay_{i}.png"
            overlay_png.save(str(overlay_path))

            # 하단 바 합성용 임시 저장
            bar_path = clips_dir / f"bar_{i}.png"
            bottom_bar.save(str(bar_path))

            _ffmpeg_extract_with_overlay(
                video_paths[i], str(clip_path),
                str(overlay_path), str(bar_path),
                W, H, spec.content_height, duration, FPS,
            )
            clip_paths.append(str(clip_path))

            # 프리뷰: 영상 첫 프레임 캡처
            _save_video_preview(str(clip_path), previews_dir / f"scene_{i}.jpg")
        else:
            # 사진 씬: 정적 프레임 → 영상 클립
            photo_idx = min(scene.media_index, max(0, len(photos) - 1))
            frame = renderer.render_scene(layout, photos, photo_idx)
            frame.save(previews_dir / f"scene_{i}.jpg", quality=85)

            frame_path = clips_dir / f"still_{i}.jpg"
            frame.save(str(frame_path), quality=95)

            clip_path = clips_dir / f"clip_{i}.mp4"
            _ffmpeg_still_to_clip(str(frame_path), str(clip_path),
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
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        video_out,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)


def _ffmpeg_still_to_clip(
    image_path: str, video_out: str,
    width: int, height: int,
    duration: float, fps: int,
):
    """정지 이미지 → 영상 클립 변환"""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-t", str(duration),
        "-r", str(fps),
        "-vf", f"scale={width}:{height}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        video_out,
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)


def _ffmpeg_concat_clips(clip_paths: list[str], output_path: str, work_dir: Path):
    """클립 리스트를 순서대로 연결"""
    list_file = work_dir / "concat.txt"
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)


def _save_video_preview(video_path: str, output_path: Path):
    """영상 첫 프레임을 프리뷰 이미지로 저장"""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-frames:v", "1", "-q:v", "2",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)
