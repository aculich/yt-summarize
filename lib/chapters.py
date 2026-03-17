"""
Parse yt-dlp info.json chapters and slice transcript by time.
Expects SRT or VTT content with timecodes to assign cues to chapters.
"""
import json
from pathlib import Path
from typing import List, Tuple


def parse_srt_timestamps(text: str) -> List[Tuple[float, str]]:
    """Parse SRT and return list of (start_seconds, cue_text)."""
    import re
    out = []
    block = []
    for line in text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            if block:
                # Parse block: expect "HH:MM:SS,mmm --> ..." then lines of text
                time_line = None
                text_lines = []
                for b in block:
                    if " --> " in b:
                        time_line = b
                    elif time_line is not None:
                        text_lines.append(b)
                if time_line and text_lines:
                    m = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", time_line)
                    if m:
                        h, m_, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                        start = h * 3600 + m_ * 60 + s + ms / 1000.0
                        out.append((start, " ".join(text_lines)))
            block = []
            continue
        block.append(line_stripped)
    if block:
        time_line = None
        text_lines = []
        for b in block:
            if " --> " in b:
                time_line = b
            elif time_line is not None:
                text_lines.append(b)
        if time_line and text_lines:
            m = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", time_line)
            if m:
                h, m_, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                start = h * 3600 + m_ * 60 + s + ms / 1000.0
                out.append((start, " ".join(text_lines)))
    return out


def parse_vtt_timestamps(text: str) -> List[Tuple[float, str]]:
    """Parse WebVTT and return list of (start_seconds, cue_text)."""
    import re
    blocks = []
    current = []
    for line in text.splitlines():
        line_stripped = line.strip()
        if " --> " in line_stripped:
            if current:
                blocks.append(current)
            current = [line_stripped]
        elif current and line_stripped and not line_stripped.upper().startswith("WEBVTT") and not line_stripped.startswith("NOTE"):
            current.append(line_stripped)
        elif not line_stripped:
            if current:
                blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    out = []
    for block in blocks:
        if not block:
            continue
        time_line = block[0]
        m = re.match(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})", time_line)
        if m:
            h, m_, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            start = h * 3600 + m_ * 60 + s + ms / 1000.0
            text = " ".join(block[1:]) if len(block) > 1 else ""
            if text:
                out.append((start, text))
    return out


def load_chapters(info_path: Path) -> List[dict]:
    """Load chapters from yt-dlp info.json. Each chapter has start_time, end_time, title."""
    data = json.loads(info_path.read_text(encoding="utf-8"))
    chapters = data.get("chapters") or []
    return chapters


def slice_transcript_by_chapters(
    timed_cues: List[Tuple[float, str]],
    chapters: List[dict],
) -> List[Tuple[str, str]]:
    """Return list of (chapter_title, segment_text) for each chapter."""
    result = []
    for ch in chapters:
        start = float(ch.get("start_time", 0))
        end = float(ch.get("end_time", 1e9))
        title = ch.get("title") or "Chapter"
        parts = [text for t, text in timed_cues if start <= t < end]
        result.append((title, " ".join(parts).strip()))
    return result
