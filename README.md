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

## LLM model and cost (March 2026)

The default model is **gpt-4o-mini** (OpenAI’s 4o family). We use it because it’s cost‑efficient for summarization and gives a good quality/speed tradeoff; transcript summarization doesn’t require the latest flagship model.

**Approximate pricing (March 2026):**

| Model        | Input (per 1M tokens) | Output (per 1M tokens) |
|-------------|------------------------|-------------------------|
| gpt-4o-mini | ~$0.15                 | ~$0.60                  |
| gpt-4o      | higher                 | higher                  |
| gpt-5.x     | varies                 | varies                  |

A typical 30–60 minute video transcript is on the order of 10k–30k input tokens and a few thousand output tokens per run, so whole-transcript or chapter runs usually cost a few cents with gpt-4o-mini. For up‑to‑date numbers, see [OpenAI pricing](https://openai.com/api/pricing/).

**Changing the model:** You can override the model in two ways:

1. **CLI:** `./yt-summarize --model gpt-4o 'https://...'` (or any model id supported by llm).
2. **Templates:** Edit the `model:` line in `prompts/whole.yaml`, `prompts/chapter.yaml`, etc. The `--model` flag takes precedence over the template when set.

So you can stick with 4o-mini for cheap batch runs or switch to gpt-4o, gpt-5, or another provider/model that llm supports.

## Usage

By default, the summary is written into the cache directory for the video and printed to stdout. Use `-o FILE` only when you want a different path or to suppress stdout.

Example video: [Andrej Karpathy: Software Is Changing (Again)](https://www.youtube.com/watch?v=LCEmiRjPEtQ).

```bash
# Whole-transcript summary: writes cache/LCEmiRjPEtQ/summary.md and prints it
./yt-summarize 'https://www.youtube.com/watch?v=LCEmiRjPEtQ'

# Chapter mode: writes cache/LCEmiRjPEtQ/summary-chapters.md and prints it
./yt-summarize --mode chapters 'https://www.youtube.com/watch?v=LCEmiRjPEtQ'

# Write summary and transcript to specific files (no stdout)
./yt-summarize -o summary.md -T transcript.txt 'https://www.youtube.com/watch?v=LCEmiRjPEtQ'

# Keep SRT timestamps in transcript and ask LLM to cite them in pull quotes
./yt-summarize --keep-timestamps -o summary.md 'https://www.youtube.com/watch?v=LCEmiRjPEtQ'

# Chapter mode + merge into one overall summary at the end
./yt-summarize --mode chapters --merge 'https://www.youtube.com/watch?v=LCEmiRjPEtQ'

# Force re-download (ignore cache)
./yt-summarize --no-cache 'https://www.youtube.com/watch?v=LCEmiRjPEtQ'

# Custom cache directory
./yt-summarize --cache-dir /path/to/cache 'https://...'
```

### Sample output (whole-transcript)

Running on the Karpathy video produces markdown in the shape of the prompt template. A shortened example:

```markdown
## Overview
Andrej Karpathy discusses how software development is shifting again—toward AI-augmented workflows, smaller teams, and “vibe coding.” He covers implications for tooling, hiring, and where to place bets as a developer.

## Key points
- Software 1.0 (hand-written) and 2.0 (learned) are being joined by a new, AI-assisted way of building.
- GUIs for LLMs are still early; the best interfaces are yet to be invented.
- Advice for developers: learn the stack, use AI to move faster, and focus on high-leverage work.

## Pull quotes
- "There is a new kind of coding that I call vibe coding where you fully give into the vibes."
- "The GUI for this hasn’t been invented yet."

## Target audience
Developers, technical leads, and anyone thinking about how AI changes building software.

## Actionable takeaways
- Experiment with AI coding tools (e.g. Cursor, Copilot) and voice-driven workflows.
- Invest in fundamentals plus one or two high-signal AI-native workflows.
```

### Sample output (chapter mode)

With `--mode chapters`, each chapter is summarized and concatenated. With `--merge`, an overall summary is prepended:

```markdown
# Overall summary
[Single merged summary of the full video.]

---

# Per-chapter summaries

## Chapter 1: Intro
[Overview], [Key points], [Pull quotes], [Actionable takeaways] for this segment.

## Chapter 2: Software 1.0 and 2.0
...

## Chapter 3: Where we are now
...
```

## Options

| Option | Description |
|--------|-------------|
| `-o FILE` | Write summary to FILE instead of the default cache path (and do not print to stdout) |
| `-T FILE` | Write the transcript (as fed to llm) to FILE |
| `--strip` | Plain transcript only, no timestamps (default) |
| `--keep-timestamps` | Keep SRT/VTT timestamps; LLM will cite them in pull quotes |
| `--mode whole` | One summary for the full transcript (default) |
| `--mode chapters` | Per-chapter summaries; falls back to whole if no chapters |
| `--merge` | With `--mode chapters`, add a final merged overall summary |
| `--no-cache` | Re-run yt-dlp and overwrite cache |
| `--cache-dir DIR` | Use DIR for cache (default: `./cache` or `$YT_SUMMARIZE_CACHE` or `~/.cache/yt-summarize`) |
| `--model MODEL` | Override model passed to llm (default from template: gpt-4o-mini; see [LLM model and cost](#llm-model-and-cost-march-2026)) |

## Cache

Raw yt-dlp output and summaries are stored under the cache directory by video ID (e.g. `cache/LCEmiRjPEtQ/` for the Karpathy example):

```
cache/<video_id>/
├── subs.info.json      # Chapters and metadata (yt-dlp -o subs)
├── subs.en.srt         # Subtitle file(s)
├── subs.en.vtt
├── summary.md          # Whole-transcript summary (default output)
└── summary-chapters.md # Chapter-mode summary (default output when --mode chapters)
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
