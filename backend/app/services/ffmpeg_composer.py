"""FFmpeg 합성: 프레임 시퀀스 / 비디오 + BGM → 최종 MP4"""
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

    logger.info(f"[compose_from_video] cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        stderr = result.stderr
        err_head = stderr[:500] if len(stderr) > 1000 else ""
        err_tail = stderr[-500:]
        raise RuntimeError(f"FFmpeg 합성 실패:\n[HEAD] {err_head}\n[TAIL] {err_tail}")

    return output_path
