# yt-summarize

Standalone CLI that chains **yt-dlp** (transcript + metadata) and **llm** (Simon Willison’s [llm](https://llm.datasette.io/)) to summarize YouTube videos. Supports whole-transcript or chapter-by-chapter output, optional timestamps in the transcript, and caches raw yt-dlp output for reuse.

## Install dependencies

Run from the `yt-summarize` directory:

```bash
./install-deps.sh
```

Or manually with **uv** (recommended):

```bash
uv venv && uv pip install yt-dlp llm
```

Or with **pip**:

```bash
pip install yt-dlp llm
```

Set your API key for llm (e.g. OpenAI):

```bash
export OPENAI_API_KEY='your-key'
# or use llm's config: llm keys set openai
```

See [llm setup](https://llm.datasette.io/en/stable/setup.html) and [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Usage

```bash
# Whole-transcript summary (plain text, no timestamps); print to stdout
./yt-summarize 'https://www.youtube.com/watch?v=VIDEO_ID'

# Write summary and transcript to files
./yt-summarize -o summary.md -T transcript.txt 'https://www.youtube.com/watch?v=VIDEO_ID'

# Keep SRT timestamps in transcript and ask LLM to cite them in pull quotes
./yt-summarize --keep-timestamps -o summary.md 'https://www.youtube.com/watch?v=VIDEO_ID'

# Chapter-by-chapter summary (requires video to have chapters)
./yt-summarize --mode chapters -o summary.md 'https://www.youtube.com/watch?v=VIDEO_ID'

# Chapter mode + merge into one overall summary at the end
./yt-summarize --mode chapters --merge -o summary.md 'https://www.youtube.com/watch?v=VIDEO_ID'

# Force re-download (ignore cache)
./yt-summarize --no-cache -o summary.md 'https://www.youtube.com/watch?v=VIDEO_ID'

# Custom cache directory
./yt-summarize --cache-dir /path/to/cache -o summary.md 'https://...'
```

## Options

| Option | Description |
|--------|-------------|
| `-o FILE` | Write summary to FILE instead of stdout |
| `-T FILE` | Write the transcript (as fed to llm) to FILE |
| `--strip` | Plain transcript only, no timestamps (default) |
| `--keep-timestamps` | Keep SRT/VTT timestamps; LLM will cite them in pull quotes |
| `--mode whole` | One summary for the full transcript (default) |
| `--mode chapters` | Per-chapter summaries; falls back to whole if no chapters |
| `--merge` | With `--mode chapters`, add a final merged overall summary |
| `--no-cache` | Re-run yt-dlp and overwrite cache |
| `--cache-dir DIR` | Use DIR for cache (default: `./cache` or `$YT_SUMMARIZE_CACHE` or `~/.cache/yt-summarize`) |
| `--model MODEL` | Pass `-m MODEL` to llm (e.g. gpt-4o-mini) |

## Cache

Raw yt-dlp output is stored under the cache directory by video ID:

```
cache/<video_id>/
├── subs.info.json   # Chapters and metadata (yt-dlp -o subs)
├── subs.en.srt      # Subtitle file(s)
└── subs.en.vtt
```

Re-runs use this cache unless you pass `--no-cache`. Different `--strip` / `--keep-timestamps` or `--mode` use the same cache and derive transcript on the fly.

## Templates

Prompts live in `prompts/` and are passed to `llm -t path/to/template.yaml`:

- **whole.yaml** – Whole transcript, plain text (no timestamps)
- **whole-timestamps.yaml** – Whole transcript with SRT timestamps; cite in pull quotes
- **chapter.yaml** – Single chapter segment
- **merge-chapters.yaml** – Merge per-chapter summaries into one

You can edit these with `llm templates edit` or by changing the YAML files.

## Repo

Self-contained; can be copied or cloned as its own Git repo and pushed to GitHub. No dependency on the parent continuous-ai repo.

## License

MIT.
