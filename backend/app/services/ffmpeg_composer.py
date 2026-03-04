"""FFmpeg 합성: 프레임 시퀀스 / 비디오 + BGM → 최종 MP4"""
import subprocess
from app.core.config import FPS, BGM_VOLUME, BGM_FADE_IN, BGM_FADE_OUT, TARGET_DURATION


def compose_from_frames(frames_dir: str, bgm_path: str,
                        output_path: str,
                        duration: float = TARGET_DURATION) -> str:
    """사진 전용: PNG 프레임 시퀀스 + BGM → MP4"""
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
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

    codec_opts = ["-c:v", "libx264", "-preset", "fast", "-crf", "20"]
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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 합성 실패: {result.stderr[-500:]}")

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

    codec_opts = ["-c:v", "libx264", "-preset", "fast", "-crf", "20"]
    if bgm_path:
        codec_opts.extend(["-c:a", "aac", "-b:a", "128k"])
    codec_opts.extend([
        "-r", str(FPS),
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 합성 실패: {result.stderr[-500:]}")

    return output_path
