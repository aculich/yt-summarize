"""
Convert SRT/VTT subtitle content to plain text or keep timestamps.
"""
import re
from pathlib import Path


def srt_to_plain(text: str) -> str:
    """Strip SRT to plain text: remove sequence numbers, timecodes, keep cue text."""
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if " --> " in line:
            continue
        lines.append(line)
    return "\n".join(lines)


def vtt_to_plain(text: str) -> str:
    """Strip WebVTT to plain text: remove header and timecodes, keep cue text."""
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("WEBVTT"):
            continue
        if line.startswith("NOTE "):
            continue
        if " --> " in line:
            continue
        lines.append(line)
    return "\n".join(lines)


def srt_to_timestamped(text: str) -> str:
    """Keep SRT structure: sequence, timecode, text. Normalize whitespace only."""
    return text.strip()


def vtt_to_timestamped(text: str) -> str:
    """Keep VTT structure; normalize whitespace only."""
    return text.strip()


def subtitle_to_text(path: Path, keep_timestamps: bool) -> str:
    """Read subtitle file and return plain text or timestamped text."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()
    if keep_timestamps:
        if ext == ".srt":
            return srt_to_timestamped(raw)
        return vtt_to_timestamped(raw)
    if ext == ".srt":
        return srt_to_plain(raw)
    if ext == ".vtt":
        return vtt_to_plain(raw)
    # default: try strip (e.g. other formats)
    return srt_to_plain(raw)
