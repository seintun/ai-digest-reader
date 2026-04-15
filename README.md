# AI News Digest Aggregator

Quick daily digest of hot AI content from Reddit + Hacker News.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Generate today's digest (saves to output/YYYY-MM-DD/digest-YYYY-MM-DD-HHMMSS.md)
python digest.py

# Custom output directory
python digest.py --output-dir my-digests/

# Limit posts per source
python digest.py --limit 5

# Fetch specific subreddits only
python digest.py --subreddits ArtificialIntelligence LocalLLaMA
```

## Output

Digest files are auto-named with timestamp:
```
output/
└── 2026-04-15/
    ├── digest-2026-04-15-090000.md
    ├── digest-2026-04-15-152501.md
    └── digest-2026-04-15-183045.md
```

Multiple runs same day get unique timestamps (no overwrite).

## Sources
- Reddit: r/ArtificialIntelligence, r/LocalLLaMA, r/ChatGPT, r/MachineLearning
- Hacker News: Front page