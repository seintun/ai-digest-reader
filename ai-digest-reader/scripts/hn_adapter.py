import requests
from typing import List
from .base import SourceAdapter, Story


HN_API_URL = 'https://hacker-news.firebaseio.com/v0'
POST_LIMIT = 10


class HNAdapter(SourceAdapter):
    def __init__(self, limit: int | None = None):
        self.limit = limit if limit is not None else POST_LIMIT

    def fetch(self) -> List[Story]:
        stories = []
        try:
            top_ids_url = f'{HN_API_URL}/topstories.json'
            response = requests.get(top_ids_url, timeout=10)
            response.raise_for_status()
            top_ids = response.json()[:self.limit]

            for idx, story_id in enumerate(top_ids):
                try:
                    story_url = f'{HN_API_URL}/item/{story_id}.json'
                    story_response = requests.get(story_url, timeout=10)
                    story_response.raise_for_status()
                    story_data = story_response.json()

                    if story_data and story_data.get('type') == 'story':
                        story = Story(
                            story_id=f'hn-{idx}',
                            title=story_data.get('title', ''),
                            url=story_data.get('url', ''),
                            score=story_data.get('score', 0),
                            comments=story_data.get('descendants', 0),
                            author=story_data.get('by', 'unknown')
                        )
                        stories.append(story)
                except Exception as e:
                    print(f'Error fetching HN story {story_id}: {e}', file=__import__('sys').stderr)
        except Exception as e:
            print(f'Error fetching HN top stories: {e}', file=__import__('sys').stderr)
        return stories

    def get_source_name(self) -> str:
        return 'hn'
