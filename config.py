SUBREDDITS = [
    "ArtificialIntelligence",
    "LocalLLaMA",
    "ChatGPT",
    "MachineLearning",
    "technology",
    "programming",
    "science",
    "worldnews",
    "Futurology",
    "singularity",
    "startups",
]

SUBREDDIT_CATEGORIES: dict[str, str] = {
    "ArtificialIntelligence": "AI & ML",
    "LocalLLaMA": "AI & ML",
    "ChatGPT": "AI & ML",
    "MachineLearning": "AI & ML",
    "technology": "Tech",
    "programming": "Tech",
    "science": "Science",
    "worldnews": "World News",
    "Futurology": "Futurology",
    "singularity": "Futurology",
    "startups": "Startups",
}

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
]
