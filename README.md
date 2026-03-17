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

The default model is **gpt-4o-mini** (OpenAI’s 4o family). We use it because it’s cost‑efficient for summarization and gives a good quality/speed tradeoff; transcript summarization doesn’t require the latest flagship model. The [llm](https://llm.datasette.io/) CLI supports multiple providers, so you can point yt-summarize at OpenAI, Anthropic, Google, or others by setting API keys and passing the right model id.

All figures below are **approximate USD per 1M tokens** (input / output). Pricing changes over time; check each provider’s official page for current numbers.

### OpenAI

| Model        | Input (per 1M) | Output (per 1M) | Notes                    |
|-------------|----------------|-----------------|--------------------------|
| gpt-4o-mini | $0.15          | $0.60           | Default; very cheap      |
| gpt-4.1-mini| $0.40          | $1.60           | 128K context             |
| gpt-4o      | $2.50          | $10.00          | Legacy 4o                |
| gpt-4.1     | higher         | higher          | Production 4.1           |
| gpt-5-mini  | $0.25          | $2.00           | Cheap 5 family           |
| gpt-5       | $1.25          | $10.00          | Mid-tier 5               |
| gpt-5.4     | $2.50          | $15.00          | Flagship                 |

- **Cached input** is much cheaper (e.g. ~75–90% off) when you reuse long context.
- **Batch API** and **Flex** tiers can reduce cost further.
- Official: [OpenAI pricing](https://openai.com/api/pricing/).

### Anthropic (Claude)

| Model            | Input (per 1M) | Output (per 1M) | Notes              |
|------------------|----------------|-----------------|--------------------|
| claude-haiku-4-5 | $1.00          | $5.00           | Fast, cheap         |
| claude-sonnet-4-5 / 4-6 | $3.00   | $15.00          | Balanced            |
| claude-opus-4-5 / 4-6   | $5.00   | $25.00          | Flagship            |

- Long-context (>200K input) tiers cost more (e.g. Opus ~$10 / $37.50).
- Prompt caching: cache reads ~90% cheaper than standard input.
- Official: [Anthropic pricing](https://docs.anthropic.com/en/docs/about-claude/pricing).

### Google (Gemini)

| Model                    | Input (per 1M) | Output (per 1M) | Notes                |
|--------------------------|----------------|-----------------|----------------------|
| gemini-2.5-flash         | ~$0.15         | ~$0.60          | Cheap, fast          |
| gemini-2.5-flash-lite    | lower          | lower           | Lightweight          |
| gemini-2.5-pro           | higher         | higher          | Pro 2.5              |
| gemini-3-flash-preview   | ~$0.25         | ~$0.75          | 3 family, efficient  |
| gemini-3.1-flash-lite-preview | $0.25    | $0.75+          | 3.1 entry            |
| gemini-3-pro-preview     | ~$2.00         | ~$12.00         | 3 Pro (tiered >200K) |
| gemini-3.1-pro-preview   | $2.00          | $12.00          | 3.1 Pro              |

- Gemini 3.x often has tiered pricing for inputs >200K (e.g. 2× input rate).
- Official: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).

### Other providers (llm)

The llm CLI can use additional backends (e.g. **Meta Llama**, **Ollama** for local models). Install the relevant plugin and set keys; then pass the model id with `--model`. See [llm plugins](https://llm.datasette.io/en/stable/plugins.html).

### Typical cost per run

A 30–60 minute video transcript is roughly **10k–30k input tokens** and **2k–6k output tokens** per summary. With **gpt-4o-mini** that’s about **$0.01–0.03** per whole-transcript run; chapter mode costs more (one call per chapter). Using **gpt-5-mini** or **gemini-2.5-flash** is in the same ballpark; **Claude Haiku** or **gpt-4o** is a few cents more; flagship models (Opus, gpt-5.4, Gemini 3.1 Pro) can be 10–30× more per run.

### Changing the model

1. **CLI:** `./yt-summarize --model MODEL_ID 'https://...'`  
   Examples: `--model gpt-4o`, `--model claude-sonnet-4-5-20250929`, `--model gemini-2.5-flash`.
2. **Templates:** Edit the `model:` line in `prompts/whole.yaml`, `prompts/chapter.yaml`, `prompts/whole-timestamps.yaml`, and `prompts/merge-chapters.yaml`. The `--model` flag overrides the template when set.

Use different providers by configuring llm (e.g. `llm keys set anthropic`, `llm install llm-gemini`) and then passing the corresponding model id to `--model`.

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
