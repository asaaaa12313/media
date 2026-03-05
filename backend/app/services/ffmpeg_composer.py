"""FFmpeg 합성: 프레임 시퀀스 / 비디오 + BGM → 최종 MP4

xfade_concat: 클립 기반 파이프라인용 전환 합성
compose_from_*: 레거시 프레임 시퀀스 파이프라인
"""
import logging
import subprocess
from pathlib import Path
from app.core.config import FPS, BGM_VOLUME, BGM_FADE_IN, BGM_FADE_OUT, TARGET_DURATION

logger = logging.getLogger(__name__)


def compose_from_frames(frames_dir: str, bgm_path: str,
                        output_path: str,
                        duration: float = TARGET_DURATION) -> str:
    """사진 전용: PNG 프레임 시퀀스 + BGM → MP4"""
    # 프레임 파일 존재 여부 검증
    fd = Path(frames_dir)
    frame_files = sorted(fd.glob("[0-9]*.jpg"))
    logger.info(f"[compose_from_frames] frames_dir={frames_dir}, frame_count={len(frame_files)}")
    if frame_files:
        logger.info(f"  first={frame_files[0].name}, last={frame_files[-1].name}, "
                     f"first_size={frame_files[0].stat().st_size}")
    if not frame_files:
        raise RuntimeError(f"프레임 파일 없음: {frames_dir}")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-start_number", "0",
        "-i", f"{frames_dir}/%05d.jpg",
    ]

    if bgm_path:
        cmd.extend(["-i", bgm_path])

    filter_parts = []
    if bgm_path:
        filter_parts.append(
            f"[1:a]atrim=0:{duration},"
            f"afade=t=in:st=0:d={BGM_FADE_IN},"
            f"afade=t=out:st={duration - BGM_FADE_OUT}:d={BGM_FADE_OUT},"
            f"volume={BGM_VOLUME}[bgm]"
        )

    if filter_parts:
        cmd.extend(["-filter_complex", ";".join(filter_parts)])
        cmd.extend(["-map", "0:v", "-map", "[bgm]"])
    else:
        cmd.extend(["-map", "0:v"])

    codec_opts = [
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-threads", "2", "-x264-params", "threads=2:lookahead_threads=1",
    ]
    if bgm_path:
        codec_opts.extend(["-c:a", "aac", "-b:a", "128k"])
    codec_opts.extend([
        "-r", str(FPS),
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])
    cmd.extend(codec_opts)

    logger.info(f"[compose_from_frames] cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        stderr = result.stderr
        # 앞부분(원인) + 뒷부분(진행상태) 모두 캡처
        err_head = stderr[:500] if len(stderr) > 1000 else ""
        err_tail = stderr[-500:]
        raise RuntimeError(f"FFmpeg 합성 실패:\n[HEAD] {err_head}\n[TAIL] {err_tail}")

    return output_path


def compose_from_video(video_path: str, bgm_path: str,
                       output_path: str,
                       duration: float = TARGET_DURATION) -> str:
    """영상 포함: 합성된 비디오 + BGM → 최종 MP4"""
    cmd = ["ffmpeg", "-y", "-i", video_path]

    if bgm_path:
        cmd.extend(["-i", bgm_path])

    filter_parts = []
    if bgm_path:
        filter_parts.append(
            f"[1:a]atrim=0:{duration},"
            f"afade=t=in:st=0:d={BGM_FADE_IN},"
            f"afade=t=out:st={duration - BGM_FADE_OUT}:d={BGM_FADE_OUT},"
            f"volume={BGM_VOLUME}[bgm]"
        )

    if filter_parts:
        cmd.extend(["-filter_complex", ";".join(filter_parts)])
        cmd.extend(["-map", "0:v", "-map", "[bgm]"])
    else:
        cmd.extend(["-map", "0:v"])

    codec_opts = [
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-threads", "2", "-x264-params", "threads=2:lookahead_threads=1",
    ]
    if bgm_path:
        codec_opts.extend(["-c:a", "aac", "-b:a", "128k"])
    codec_opts.extend([
        "-r", str(FPS),
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])
    cmd.extend(codec_opts)

    logger.info(f"[compose_from_video] cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        stderr = result.stderr
        err_head = stderr[:500] if len(stderr) > 1000 else ""
        err_tail = stderr[-500:]
        raise RuntimeError(f"FFmpeg 합성 실패:\n[HEAD] {err_head}\n[TAIL] {err_tail}")

    return output_path


def xfade_concat(
    clip_paths: list[str],
    clip_durations: list[float],
    output_path: str,
    transition_duration: float = 0.8,
    transition: str | list[str] = "fade",
) -> str:
    """MP4 클립들을 xfade 전환 효과로 합성

    Args:
        clip_paths: 개별 씬 MP4 경로 리스트
        clip_durations: 각 클립의 길이 (초)
        output_path: 출력 MP4 경로
        transition_duration: 전환 효과 길이 (초)
        transition: 단일 전환 타입 또는 씬 경계별 전환 리스트
    Returns:
        출력 파일 경로
    """
    n = len(clip_paths)
    if n == 0:
        raise RuntimeError("xfade_concat: 클립 없음")

    if n == 1:
        import shutil
        shutil.copyfile(clip_paths[0], output_path)
        return output_path

    # transition을 리스트로 정규화
    if isinstance(transition, str):
        transitions = [transition] * (n - 1)
    else:
        transitions = list(transition)
        # 부족하면 순환
        while len(transitions) < n - 1:
            transitions.append(transitions[len(transitions) % len(transition)])

    cmd = ["ffmpeg", "-y"]
    for p in clip_paths:
        cmd.extend(["-i", p])

    filter_parts = []
    cumulative_offset = clip_durations[0] - transition_duration

    for i in range(1, n):
        if i == 1:
            src_label = "[0][1]"
        else:
            src_label = f"[v{i-2:02d}][{i}]"

        if i == n - 1:
            out_label = "[vout]"
        else:
            out_label = f"[v{i-1:02d}]"

        t = transitions[i - 1]
        filter_parts.append(
            f"{src_label}xfade=transition={t}:"
            f"duration={transition_duration}:"
            f"offset={cumulative_offset:.2f}{out_label}"
        )

        if i < n - 1:
            cumulative_offset += clip_durations[i] - transition_duration

    filter_str = ";".join(filter_parts)
    cmd.extend(["-filter_complex", filter_str])
    cmd.extend(["-map", "[vout]", "-an"])
    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-threads", "2", "-x264-params", "threads=2:lookahead_threads=1",
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])

    logger.info(f"[xfade_concat] {n} clips, transitions={transitions}, dur={transition_duration}s")
    logger.info(f"[xfade_concat] filter: {filter_str}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        logger.error(f"[xfade_concat] FFmpeg stderr:\n{result.stderr}")
        logger.warning("[xfade_concat] xfade 실패, 단순 concat 폴백")
        return _simple_concat_fallback(clip_paths, output_path)

    return output_path


def _simple_concat_fallback(clip_paths: list[str], output_path: str) -> str:
    """xfade 실패 시 단순 concat 폴백"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")
        list_file = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"concat 폴백 실패: {result.stderr[-500:]}")
    return output_path


def compose_clips_with_bgm(
    video_path: str, bgm_path: str,
    output_path: str,
    duration: float = TARGET_DURATION,
) -> str:
    """합성된 영상 + BGM → 최종 MP4 (클립 기반 파이프라인용)"""
    cmd = ["ffmpeg", "-y", "-i", video_path]

    if bgm_path:
        cmd.extend(["-i", bgm_path])

    filter_parts = []
    if bgm_path:
        filter_parts.append(
            f"[1:a]atrim=0:{duration},"
            f"afade=t=in:st=0:d={BGM_FADE_IN},"
            f"afade=t=out:st={duration - BGM_FADE_OUT}:d={BGM_FADE_OUT},"
            f"volume={BGM_VOLUME}[bgm]"
        )

    if filter_parts:
        cmd.extend(["-filter_complex", ";".join(filter_parts)])
        cmd.extend(["-map", "0:v", "-map", "[bgm]"])
    else:
        cmd.extend(["-map", "0:v"])

    codec_opts = [
        "-c:v", "copy",  # 영상은 이미 인코딩됨, 복사만
    ]
    if bgm_path:
        codec_opts.extend(["-c:a", "aac", "-b:a", "128k"])
    codec_opts.extend([
        "-t", str(duration),
        "-movflags", "+faststart",
        output_path,
    ])
    cmd.extend(codec_opts)

    logger.info(f"[compose_clips_with_bgm] cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        stderr = result.stderr
        raise RuntimeError(f"BGM 합성 실패: {stderr[-500:]}")

    return output_path
