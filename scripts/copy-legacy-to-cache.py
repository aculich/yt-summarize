#!/usr/bin/env python3
"""
Copy a legacy-src output/youtube/VIDEOID__title/ dir into yt-summarize cache.
Converts transcript.json3 to SRT if needed; copies info.json.
Usage: python copy-legacy-to-cache.py <legacy_video_dir> [cache_dir]
"""
import json
import re
import sys
from pathlib import Path


def json3_to_srt(json3_path: Path) -> str:
    """Convert YouTube JSON3 transcript to SRT."""
    raw = json3_path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except Exception:
        return ""
    events = data.get("events") if isinstance(data, dict) else []
    if not events:
        return ""

    def ms_to_srt(ms: float) -> str:
        s = max(0, ms / 1000.0)
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = s % 60
        return f"{h:02d}:{m:02d}:{int(sec):02d},{int((sec % 1) * 1000):03d}"

    lines = []
    idx = 0
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            continue
        t_start_ms = ev.get("tStartMs", 0)
        try:
            t_start_ms = float(t_start_ms)
        except (TypeError, ValueError):
            continue
        segs = ev.get("segs") or []
        text_parts = [s["utf8"].strip() for s in segs if isinstance(s, dict) and s.get("utf8")]
        text = " ".join(text_parts).strip()
        if not text:
            continue
        t_end_ms = t_start_ms + 3000
        if i + 1 < len(events) and isinstance(events[i + 1], dict):
            next_start = events[i + 1].get("tStartMs")
            if next_start is not None:
                try:
                    t_end_ms = float(next_start)
                except (TypeError, ValueError):
                    pass
        idx += 1
        lines.append(str(idx))
        lines.append(f"{ms_to_srt(t_start_ms)} --> {ms_to_srt(t_end_ms)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: copy-legacy-to-cache.py <legacy_video_dir> [cache_dir]", file=sys.stderr)
        return 1
    legacy_dir = Path(sys.argv[1]).resolve()
    if not legacy_dir.is_dir():
        print(f"Not a directory: {legacy_dir}", file=sys.stderr)
        return 1
    # video_id is the first segment of dir name before __
    name = legacy_dir.name
    if "__" in name:
        video_id = name.split("__")[0]
    else:
        video_id = name
    if not re.match(r"^[a-zA-Z0-9_-]{10,}$", video_id):
        print(f"Could not infer video_id from dir name: {name}", file=sys.stderr)
        return 1
    cache_root = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else (Path(__file__).resolve().parent.parent / "cache")
    cache_dir = cache_root / video_id
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Subtitle: prefer .srt/.vtt from legacy, else convert .json3 to .srt
    sub_written = False
    for stem, ext in (("transcript", ".srt"), ("transcript", ".vtt")):
        src = legacy_dir / f"{stem}{ext}"
        if src.exists():
            dst = cache_dir / f"subs.en{ext}"
            dst.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            print(f"Copied {src.name} -> {dst}")
            sub_written = True
            break
    if not sub_written and (legacy_dir / "transcript.json3").exists():
        srt = json3_to_srt(legacy_dir / "transcript.json3")
        if srt:
            (cache_dir / "subs.en.srt").write_text(srt, encoding="utf-8")
            print(f"Converted transcript.json3 -> cache/{video_id}/subs.en.srt")
            sub_written = True
    if not sub_written:
        print("No transcript.json3, .srt, or .vtt found in source dir", file=sys.stderr)
        return 1

    # Info JSON (for chapters)
    for name in ("info.json",):
        src = legacy_dir / name
        if src.exists():
            dst = cache_dir / "subs.info.json"
            dst.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            print(f"Copied {name} -> {dst.name}")
            break

    print(f"Cache ready: {cache_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
