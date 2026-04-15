import requests
from typing import List
from .base import SourceAdapter, Story


SUBREDDITS = [
    'r/ArtificialIntelligence',
    'r/LocalLLaMA',
    'r/ChatGPT',
    'r/MachineLearning'
]
POST_LIMIT = 10


class RedditAdapter(SourceAdapter):
    def __init__(self, subreddits: List[str] | None = None, limit: int | None = None):
        self.subreddits = subreddits if subreddits is not None else SUBREDDITS
        self.limit = limit if limit is not None else POST_LIMIT

    def fetch(self) -> List[Story]:
        stories = []
        for idx, subreddit in enumerate(self.subreddits):
            try:
                url = f'https://www.reddit.com/{subreddit}/hot.json?limit={self.limit}'
                headers = {'User-Agent': 'AI-Digest-Reader/1.0'}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                for post in data.get('data', {}).get('children', []):
                    post_data = post['data']
                    story = Story(
                        story_id=f'rd-{idx}-{len(stories)}',
                        title=post_data.get('title', ''),
                        url=post_data.get('url', ''),
                        score=post_data.get('score', 0),
                        comments=post_data.get('num_comments', 0),
                        author=post_data.get('author', 'unknown')
                    )
                    stories.append(story)
            except Exception as e:
                print(f'Error fetching {subreddit}: {e}', file=__import__('sys').stderr)
        return stories

    def get_source_name(self) -> str:
        return 'reddit'
