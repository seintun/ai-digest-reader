REDDIT_SOURCES: list[dict[str, str]] = [
    # AI & ML
    {"name": "ArtificialIntelligence", "category": "AI & ML"},
    {"name": "LocalLLaMA", "category": "AI & ML"},
    {"name": "ChatGPT", "category": "AI & ML"},
    {"name": "MachineLearning", "category": "AI & ML"},
    {"name": "singularity", "category": "AI & ML"},
    {"name": "artificial", "category": "AI & ML"},
    {"name": "OpenAI", "category": "AI & ML"},
    {"name": "ClaudeAI", "category": "AI & ML"},
    {"name": "GeminiAI", "category": "AI & ML"},
    # Tech
    {"name": "technology", "category": "Tech"},
    {"name": "programming", "category": "Tech"},
    {"name": "ExperiencedDevs", "category": "Tech"},
    {"name": "selfhosted", "category": "Tech"},
    {"name": "devops", "category": "Tech"},
    # Security
    {"name": "netsec", "category": "Security"},
    # Science
    {"name": "science", "category": "Science"},
    {"name": "space", "category": "Science"},
    {"name": "EverythingScience", "category": "Science"},
    # World News
    {"name": "worldnews", "category": "World News"},
    {"name": "geopolitics", "category": "World News"},
    # Business & Startups
    {"name": "startups", "category": "Startups"},
    {"name": "economics", "category": "Business"},
    {"name": "YCombinator", "category": "Startups"},
    # Futurology
    {"name": "Futurology", "category": "Futurology"},
]

# Derived — no manual sync needed
SUBREDDITS: list[str] = [s["name"] for s in REDDIT_SOURCES]
SUBREDDIT_CATEGORIES: dict[str, str] = {s["name"]: s["category"] for s in REDDIT_SOURCES}

HN_API_URL = "https://hacker-news.firebaseio.com/v0"

HN_CATEGORY = "Tech"

POST_LIMIT = 10

DATE_FORMAT = "%Y-%m-%d"

RSS_FEEDS = [
    {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "category": "Tech"},
    {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge", "category": "Tech"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "name": "Ars Technica", "category": "Tech"},
    {"url": "https://www.wired.com/feed/rss", "name": "Wired", "category": "Tech"},
    {"url": "https://rss.slashdot.org/Slashdot/slashdotMain", "name": "Slashdot", "category": "Tech"},
    {"url": "http://export.arxiv.org/rss/cs.AI", "name": "ArXiv AI", "category": "AI & ML"},
    {"url": "http://export.arxiv.org/rss/cs.LG", "name": "ArXiv ML", "category": "AI & ML"},
    {"url": "https://www.technologyreview.com/feed/", "name": "MIT Tech Review", "category": "Tech"},
    {"url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "name": "BBC Tech", "category": "Tech"},
    {"url": "https://feeds.reuters.com/reuters/technologyNews", "name": "Reuters Tech", "category": "Tech"},
    {"url": "https://tldr.tech/api/rss/tech", "name": "TLDR Tech", "category": "Tech"},
    {"url": "https://tldr.tech/api/rss/ai", "name": "TLDR AI", "category": "AI & ML"},
    {"url": "https://charonhub.deeplearning.ai/rss/", "name": "The Batch", "category": "AI & ML"},
    {"url": "https://jack-clark.net/feed", "name": "Import AI", "category": "AI & ML"},
]
