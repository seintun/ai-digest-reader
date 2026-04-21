# Implementation Design: Content-Aware Ranking & Summarization for DailyDigest

**Date**: 2026-04-21  
**Author**: Claude Code  
**Status**: Approved for implementation

## Overview
This document outlines the implementation plan for adding content-aware ranking and summarization to DailyDigest. The system will scrape article content, intelligently rank stories, and generate AI summaries based on actual article text rather than just metadata.

## Approved Approach
**Approach 1**: Follow the existing spec exactly with phased implementation over 4 weeks.

## Architecture

### System Components
```
digest.py (orchestrator)
├── fetchers/ (unchanged)
│   ├── reddit.py
│   ├── hn.py
│   └── rss.py
├── scraper.py (new)      # Article extraction with SQLite cache
├── ranker.py (new)       # Multi-signal scoring engine  
├── analyzer_v2.py (new)  # Content-aware summarization
└── Output: v4 digest with ranking metadata
```

### Data Flow
1. **Fetch posts** from Reddit, HN, RSS (existing functionality)
2. **Scrape content** from top 40 article URLs using `scraper.py`
3. **Rank posts** using multi-signal scoring in `ranker.py`
4. **Generate summary** using top 15 ranked articles with full content via `analyzer_v2.py`
5. **Output v4 format** with backward compatibility

## Component Specifications

### 1. scraper.py - Article Content Extractor

**Responsibilities**:
- Extract readable content from article URLs
- Implement respectful rate limiting
- Cache results in SQLite to avoid re-scraping
- Provide fallback chain for robustness

**Technical Stack**:
- **Primary**: `trafilatura>=1.6.0` (fast, handles many sites)
- **Fallback**: `readability-lxml>=0.8.1`
- **Cache**: SQLite database with schema:
  ```sql
  CREATE TABLE scraped_content (
      url_hash TEXT PRIMARY KEY,
      content TEXT,
      timestamp INTEGER,
      success BOOLEAN,
      source TEXT
  )
  ```

**Interface**:
```python
def scrape_articles(urls: List[str], max_concurrent: int = 5) -> Dict[str, Optional[str]]:
    """Scrape articles with rate limiting, returns {url: content_or_None}."""

def get_cached_content(url: str, ttl_hours: int = 24) -> Optional[str]:
    """Check cache for previously scraped content within TTL."""
```

**Implementation Details**:
- Rate limiting: 2-3s average delay between requests
- Timeout: 10s per request
- Retry: Exponential backoff (5s, 15s)
- User-Agent: "DailyDigestBot/1.0 (+https://dailydigest.vercel.app)"
- Candidate selection: `score > 10 OR comments > 5`, limit top 40 posts across sources

### 2. ranker.py - Multi-Signal Scoring Engine

**Scoring Model (0-100 scale)**:

1. **Engagement Score (40%)**
   ```python
   normalized_score = min(score / 5000, 1.0) * 20  # 0-20 points
   normalized_comments = min(comments / 1000, 1.0) * 20  # 0-20 points
   engagement = normalized_score + normalized_comments
   ```

2. **Content Quality Score (30%)**
   - LLM rates: "Rate article substance (1=clickbait, 10=substantive)"
   - Based on 200-character excerpt of scraped content
   - Batch evaluation: single prompt with all excerpts
   - Points: `(llm_rating / 10) * 30`

3. **Recency Score (15%)**
   ```python
   hours_ago = (now - post_time).total_seconds() / 3600
   recency = 15 * exp(-hours_ago / 24)  # 24-hour half-life
   ```

4. **Cross-Source Score (15%)**
   - Detect same story across Reddit + HN + RSS
   - URL similarity: same domain + similar path (Levenshtein distance < 20%)
   - Points: `5 * (number_of_sources - 1)`  # 0, 5, 10, 15

**Interface**:
```python
def rank_posts(posts: List[Dict], scraped_content: Dict[str, str]) -> List[Dict]:
    """Score and rank posts, adding rank/quality fields."""
```

### 3. analyzer_v2.py - Content-Aware Summarizer

**Enhancements over current `analyzer.py`**:
- Takes top 15 ranked articles (instead of all posts)
- Includes full article content (up to 2000 chars each)
- References specific content in analysis
- Same output schema (v2) for compatibility

**Prompt Structure**:
```
Analyze these AI/tech news stories and return a JSON summary.

## Top Stories (Ranked by Importance)
[rd-0] [95.2/100] {title}
Content: {first 2000 chars of article}
Score: {score}, Comments: {comments}, Quality: 8/10

[hn-1] [88.7/100] {title}
Content: {first 2000 chars of article}
Score: {score}, Comments: {comments}, Quality: 9/10

...
```

**Interface** (matches existing):
```python
def generate_summary(ranked_posts: List[Dict]) -> Optional[Dict[str, Any]]:
    """Generate content-aware summary, returns validated JSON or None."""
```

### 4. v4 Schema Extension

**Changes to digest.py**:
1. After fetching posts, call `scraper.scrape_candidates(top_40_posts)`
2. Call `ranker.rank_posts(all_posts, scraped_content)`
3. Pass top 15 ranked posts to `analyzer_v2.generate_summary()`
4. Output v4 format with ranking metadata

**v4 Schema**:
```json
{
  "v": 4,  // Version identifier
  "d": "2026-04-21",  // Date
  "g": "2026-04-21T12:00:00Z",  // Generation timestamp
  "r": [  // Reddit posts with new fields
    {
      "i": "rd-0",
      "t": "Title",
      "u": "https://...",
      "p": "/r/...",
      "b": "First 280 chars...",
      "s": 1234,
      "c": 567,
      "a": "author",
      "cat": "AI & ML",
      "rank": 95.2,           // 0-100 score
      "content_available": true,
      "content_quality": 8,   // LLM rating 1-10
      "excerpt": "First 200 chars of scraped content..."
    }
  ],
  "h": [...],  // HN posts (same fields)
  "rs": [...], // RSS posts (same fields)
  "summary": {...}  // Schema v2 compatible
}
```

## Dependencies

**New dependencies**:
```txt
trafilatura>=1.6.0      # Fast article extraction
readability-lxml>=0.8.1  # Fallback extractor
```

**Existing (keep)**:
```txt
requests>=2.31.0
feedparser>=6.0.10
openai>=1.12.0
```

## Implementation Phases

### Phase 1: Scraping Foundation (Week 1)
**Tasks**:
1. Create `scraper.py` with `trafilatura` + SQLite cache
2. Test extraction on sample URLs (TechCrunch, ArXiv, Medium)
3. Integrate with `digest.py` to scrape top 40 posts
4. Measure success rate and runtime impact

**Deliverables**: Working scraper, cache DB, integrated pipeline

### Phase 2: Ranking Engine (Week 2)
**Tasks**:
1. Create `ranker.py` with multi-signal scoring
2. Implement LLM content quality rating
3. Add cross-source detection
4. Test ranking vs human judgment samples

**Deliverables**: Ranked posts output, quality metrics

### Phase 3: Enhanced Summarization (Week 3)
**Tasks**:
1. Create `analyzer_v2.py` with content-aware prompts
2. Update `digest.py` to use ranked posts
3. Add v4 schema with ranking metadata
4. Verify backward compatibility

**Deliverables**: Content-aware summaries, v4 digest format

### Phase 4: Polish & Monitoring (Week 4)
**Tasks**:
1. Add comprehensive logging
2. Implement metrics collection
3. Optimize prompts for cost/quality balance
4. Document degradation procedures
5. Final integration testing

**Deliverables**: Production-ready pipeline, monitoring dashboard

## Subagent Strategy

**Hybrid Approach**:
- **Main agent**: Orchestrates implementation phases
- **Research subagent**: Evaluate `trafilatura` vs alternatives, test extraction libraries
- **Testing subagent**: Run extraction tests on diverse URLs, validate cache behavior
- **Validation subagent**: Human evaluation of ranking quality, summary improvements

**Work Coordination**:
- Daily checkpoints with main agent
- Clear interface contracts between components
- Shared test data and validation criteria

## Commit Strategy

**Frequency**: Commit at end of each day's work
**Message Format**:
```
feat: add scraper module with SQLite cache
fix: handle timeout in article extraction
test: add scraper unit tests for 10 sample URLs
docs: update README with new scraping capabilities
```

**Branch Strategy**:
- `feature/content-aware-ranking` (main feature branch)
- Sub-branches for each phase: `phase1-scraping`, `phase2-ranking`, etc.
- Merge to main after each phase completion with thorough testing

## Error Handling & Fallbacks

**Degradation Path**:
1. **Full pipeline**: Scraping → Ranking → Content-aware summary
2. **Fallback 1**: Scraping fails → Use snippets for ranking
3. **Fallback 2**: LLM ranking fails → Engagement-only ranking
4. **Fallback 3**: `analyzer_v2` fails → Use original `analyzer.py`
5. **Fallback 4**: All LLM fails → Output digest without summary

**Monitoring Metrics**:
- Scraping success rate (% of URLs with content)
- Cache hit rate
- LLM cost per run
- Total runtime
- Ranking quality (human spot-check)

## LLM Cost Estimation

| Step | Model | Input | Cost Estimate |
|------|-------|-------|---------------|
| Ranking | `moonshotai/kimi-k2.6` | 40 × 200 chars | $0.05 |
| Summarization | `moonshotai/kimi-k2.6` | 15 × 2000 chars | $0.12 |
| **Total** | | | **$0.17/run** |

**Optimizations**:
- Batch ranking evaluation in single prompt
- Truncate article content to 2000 chars for summarization
- Use OpenRouter (current provider) as primary

## Testing Strategy

### Unit Tests
- `scraper.py`: Extraction success on sample URLs, cache behavior
- `ranker.py`: Scoring calculations, edge cases
- `analyzer_v2.py`: Prompt formatting, JSON validation

### Integration Tests
- Full pipeline run with mock data
- Fallback path verification
- Cost calculation validation

### Quality Tests
- Human evaluation: Top 10 stories should be genuinely important
- A/B testing: Compare summaries with/without content
- Runtime: < 3 minutes total
- Cost: < $0.25 per run

## Success Criteria

1. **Accuracy**: Top 10 stories match human importance judgment (80%+ agreement)
2. **Cost**: < $0.25 per daily run
3. **Runtime**: < 3 minutes total (currently ~1 minute)
4. **Reliability**: Digest produces output 99% of runs
5. **User value**: Frontend shows ranked stories, summaries reference specific content

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scraping blocked by sites | Medium | Fallback to snippets, respect robots.txt |
| LLM cost exceeds budget | High | Strict truncation, batch processing |
| Runtime exceeds Vercel timeout | High | Concurrent scraping, timeouts, monitoring |
| Ranking algorithm poor quality | Medium | Human evaluation during development, tunable weights |
| Breaking existing frontend | High | v4 extends v3, backward compatibility mode |

## Next Steps

1. **User review** of this design document
2. **Invoke writing-plans skill** to create detailed implementation plan
3. **Begin Phase 1 implementation** with scraper module
4. **Daily commits** with progress updates
5. **Documentation** of architecture and AI summary process upon completion

---

*This design approved for implementation on 2026-04-21. Follow phased approach with hybrid subagent strategy.*
