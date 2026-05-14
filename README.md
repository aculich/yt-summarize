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

## LLM model and cost (May 2026)

Default behavior aligns with the **cheap** preset and OpenAI’s **GPT‑5 nano** rates ([GPT‑5 nano model](https://developers.openai.com/api/docs/models/gpt-5-nano): **$0.05 / $0.40 per 1M** input/output). Auto-selection usually picks **gpt‑5‑nano** for typical transcripts but upgrades along the ladder when estimates exceed **400K** tokens. Templates under `prompts/` default to `gpt-5-nano`; **`--model` overrides** auto-selection.

**Fastest authoritative refresh:** re-check each vendor’s pricing page ([OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [OpenAI consumer pricing hub](https://openai.com/api/pricing), Anthropic aggregators citing current Claude tiers such as [Anthropic Claude API Pricing 2026 (BuildMVPFast)](https://www.buildmvpfast.com/tools/api-pricing-estimator/anthropic), and Google’s billing hub linking [Gemini pricing](https://ai.google.dev/pricing) from [Gemini API billing FAQ](https://ai.google.dev/gemini-api/docs/billing)). Third-party calculators (e.g. [Gemini API Pricing Calculator 2026 | Inverted Stone](https://invertedstone.com/calculators/gemini-pricing)) mirror Google’s tier table when you need a quick comparison grid. Snapshots from earlier **parallel-cli** searches live in **`.attic/*.json`** for diffing over time.

### CLI presets (`--cheap` / `--deep`)

Without `--model`, the CLI **auto-selects** an OpenAI-model candidate from a built-in ladder (`lib/model_presets.py`): it estimates how many **tokens** your payload needs (transcript or chapter text + prompt overhead + reserved space for the summary), then picks the **first** ladder entry whose **advertised context window** is still large enough.

| Flag | Behavior |
|------|----------|
| *(none)* | Same as **cheap** (default preset). |
| `--cheap` | Walk the **cheap** ladder from lowest-cost models upward until one fits. |
| `--deep` | Walk the **deep** ladder (stronger models first among typical `llm` installs; wider-context models appear later so jobs that need **>272K** tokens can still succeed). |

`--model MODEL` **disables** auto-selection and passes `-m MODEL` through to `llm` (you are responsible for context limits).

| Flag | Maps to | Typical use |
|------|---------|-------------|
| *(none)* | Cheap preset + **auto** model | Default |
| `--cheap` | Cheap preset + **auto** model | Explicit cheap |
| `--deep` | Deep preset + **auto** model | Higher-quality preset |

Example overrides for **top cheap** and **top deep** picks (install provider plugins / keys as needed):

```bash
# Cheap tier examples (lowest input $/1M first — verify IDs in `llm models`)
./yt-summarize --cheap 'https://www.youtube.com/watch?v=VIDEO_ID'
./yt-summarize --model gpt-5-nano 'https://...'
./yt-summarize --model gemini-2.5-flash-lite 'https://...'    # Google; ~$0.10/$0.40 per 1M in paid-tier summaries such as [Gemini pricing explained (Mar 2026)](https://nicolalazzari.ai/articles/gemini-api-pricing-explained-2026)
./yt-summarize --model gpt-5.4-nano 'https://...'             # OpenAI; **$0.20 / $1.25** standard short-context ([Pricing | OpenAI API](https://developers.openai.com/api/docs/pricing))

# Deep tier examples
./yt-summarize --deep 'https://...'   # deep preset + context-aware model
./yt-summarize --model gpt-5.5 'https://...'
./yt-summarize --model anthropic/claude-opus-4-5-20251101 'https://...'   # **$5 / $25** per 1M cited for Claude Opus 4.7 tier at [BuildMVPFast Anthropic breakdown](https://www.buildmvpfast.com/tools/api-pricing-estimator/anthropic)
./yt-summarize --model gemini-3.1-pro-preview 'https://...'               # **$2 / $12** per 1M in paid-tier table summaries ([Gemini pricing explained](https://nicolalazzari.ai/articles/gemini-api-pricing-explained-2026))
```

If your installed `llm` build does not yet register **`gpt-5.5`**, selection stops earlier on **`gpt-4.1`** once estimates exceed smaller windows; you can always force **`--model gpt-5.5`**.

### Context windows, transcripts, and outputs

Provider docs publish a **context window** (maximum tokens the model accepts per request). Chat APIs consume that budget with **prompt tokens** (system + instructions + your transcript) **and** **completion tokens** (the markdown summary). If the transcript alone approaches the window, the model can truncate input, refuse, or error.

**Rough transcript sizing:** spoken English is often cited around **~150–200 words/minute**. Subtitles are typically **well below** raw token limits for normal videos—for example, **~400k tokens ≈ 1.5–2M characters** of subtitle text. Very long livestreams or caption-heavy exports are where context limits bite first.

**What this tool does:** `lib/model_presets.py` defines ladders like:

**Cheap ladder** (cost-conscious order; first row that fits wins)

| Model | Context used for selection |
|-------|-----------------------------|
| gpt-5-nano | 400,000 |
| gpt-4.1-nano | 1,048,576 |
| gpt-5.4-nano | 272,000 |
| gpt-5-mini | 272,000 |
| gpt-4.1-mini | 1,048,576 |
| gpt-4.1 | 1,048,576 |

**Deep ladder** (quality-first among typical installs; wider models later)

| Model | Context used for selection |
|-------|-----------------------------|
| gpt-5.2 | 272,000 |
| gpt-5 | 272,000 |
| gpt-5.1 | 400,000 |
| gpt-5.4 | 272,000 |
| gpt-5.5 | 1,048,576 |
| gpt-4.1 | 1,048,576 |

**Per job reserves** (conservative, no tokenizer dependency): prompt/template overhead **~4–4.25K** tokens plus completion headroom **~8–24K** (`whole` &lt; `chapter` &lt; `merge`). Token counts are **estimated** (`max(chars/3, words×1.6)`), so leave margin for dense text or non‑English subtitles.

**Modes:**

- **Whole transcript:** one call; requirement is based on the **full** transcript (+ reserves).
- **Chapter mode:** one call **per chapter**; selection uses the **longest** chapter segment (+ reserves), so very long single chapters can still force a wider-context model while shorter chapters stay on cheaper IDs.
- **`--merge`:** adds a final call over the **concatenated chapter summaries**; that merge step may pick a **different** model if the combined markdown needs more context than any single chapter.

Templates under `prompts/` still list a default `model:` for editors; **`llm -m …` from this CLI overrides** that when a model is chosen (auto or explicit).

All figures below remain **approximate USD per 1M tokens** (input / output). Confirm on the live pricing pages before budgeting.

### OpenAI

| Model | Input (per 1M) | Output (per 1M) | Notes |
|-------|----------------|-----------------|-------|
| gpt-5-nano | $0.05 | $0.40 | Cheap default; [model page](https://developers.openai.com/api/docs/models/gpt-5-nano) |
| gpt-5.4-nano | $0.20 | $1.25 | Standard short context ([pricing table](https://developers.openai.com/api/docs/pricing)) |
| gpt-5.4-mini | $0.75 | $4.50 | Mid “mini” tier ([pricing table](https://developers.openai.com/api/docs/pricing)) |
| gpt-5.4 | $2.50 | $15.00 | Workhorse frontier ([OpenAI API Pricing](https://openai.com/api/pricing)) |
| gpt-5.5 | $5.00 | $30.00 | New flagship standard rates ([pricing table](https://developers.openai.com/api/docs/pricing); [GPT‑5.5 announcement](https://openai.com/index/introducing-gpt-5-5/)) |
| gpt-5.5-pro | $30.00 | $180.00 | Highest tier listed ([pricing table](https://developers.openai.com/api/docs/pricing)) |

Batch / Flex rows on the same OpenAI pricing doc are roughly half of Standard for several GPT‑5.5 / GPT‑5.4 models.

### Anthropic (Claude)

| Model | Input (per 1M) | Output (per 1M) | Notes |
|-------|----------------|-----------------|-------|
| claude-haiku-4.5 | $1.00 | $5.00 | Budget Claude tier ([BuildMVPFast](https://www.buildmvpfast.com/tools/api-pricing-estimator/anthropic)) |
| claude-sonnet-4.6 | $3.00 | $15.00 | Balanced ([BuildMVPFast](https://www.buildmvpfast.com/tools/api-pricing-estimator/anthropic)) |
| claude-opus-4.7 | $5.00 | $25.00 | Flagship ([BuildMVPFast](https://www.buildmvpfast.com/tools/api-pricing-estimator/anthropic); third‑party May 2026 roundup [MetaCTO](https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration)) |

Official Anthropic page: [Anthropic pricing](https://docs.anthropic.com/en/docs/about-claude/pricing). Calculators such as [Inverted Stone — Claude](https://invertedstone.com/calculators/claude-pricing) list long-context uplifts (e.g. >200K) for Opus/Sonnet.

### Google (Gemini)

| Model | Input (per 1M) | Output (per 1M) | Notes |
|-------|----------------|-----------------|-------|
| gemini-2.5-flash-lite | $0.10 | $0.40 | Lowest tier in consolidated tables citing Google’s paid list ([Gemini pricing explained](https://nicolalazzari.ai/articles/gemini-api-pricing-explained-2026); [Inverted Stone — Gemini](https://invertedstone.com/calculators/gemini-pricing)) |
| gemini-2.5-flash | $0.30 | $2.50 | Fast mid-tier ([DeployBase Gemini 2026 overview](https://deploybase.ai/articles/gemini-api-pricing-2026)) |
| gemini-2.5-pro | $1.25 ($2.50 >200K prompt) | $10.00 ($15.00 >200K) | Tiered context ([DeployBase](https://deploybase.ai/articles/gemini-api-pricing-2026)) |
| gemini-3-flash-preview | $0.50 | $3.00 | Preview tier in tables summarizing Google pricing ([Gemini pricing explained](https://nicolalazzari.ai/articles/gemini-api-pricing-explained-2026)) |
| gemini-3.1-pro-preview | $2.00 | $12.00 | Higher preview tier ([Gemini pricing explained](https://nicolalazzari.ai/articles/gemini-api-pricing-explained-2026)) |

Billing mechanics and links to the official price list: [Gemini API billing](https://ai.google.dev/gemini-api/docs/billing). Enterprise / Vertex cadence notes (e.g. Gemini 3 pricing dates on some endpoints): [Agent Platform Pricing | Google Cloud](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing).

### Other providers (llm)

The llm CLI can use additional backends (e.g. **Ollama** for local models). Install the relevant plugin and set keys; then pass the model id with `--model`. See [llm plugins](https://llm.datasette.io/en/stable/plugins.html).

### Typical cost per run

A 30–60 minute video transcript is roughly **10k–30k input tokens** and **2k–6k output tokens** per summary. With **gpt‑5‑nano** that is on the order of **fractions of a cent** per whole‑transcript run at listed rates; chapter mode costs more (one call per chapter). Deep presets (**gpt‑5.5**, Claude Opus, Gemini 3.1 Pro) can be an order of magnitude higher.

### Changing the model

1. **CLI:** `./yt-summarize [--cheap|--deep] …` auto-selects by context, or `./yt-summarize --model MODEL_ID …` to pin a model.
2. **Templates:** Edit the `model:` line in `prompts/*.yaml`. The `--model` flag overrides the template when set.

Use different providers by configuring llm (e.g. `llm keys set anthropic`, `llm install llm-gemini`) and passing the corresponding model id.

### Regression samples (model smoke test)

After setting API keys, run:

```bash
./scripts/regression-model-presets.sh
```

This calls `llm` with a tiny fixture transcript for three **cheap** OpenAI slugs (`gpt-5-nano`, `gpt-4.1-nano`, `gpt-5-mini`) and three **deep** OpenAI slugs (`gpt-5.2`, `gpt-5`, `gpt-5.1`). If `ANTHROPIC_API_KEY` is set, it also runs `anthropic/claude-opus-4-5-20251101`. Timestamped stdout/stderr land under `regression-samples/<UTC-timestamp>/`.

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
| `--model MODEL` | Force model for `llm` (**skips** context auto-selection; template default is **gpt‑5‑nano**; see [LLM model and cost](#llm-model-and-cost-may-2026)) |
| `--cheap` | Cheap preset with **context-aware** model selection |
| `--deep` | Deep preset with **context-aware** model selection |

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
