from typing import List, Dict, Any
from datetime import datetime
from .base import SourceAdapter, Story


class Aggregator:
    def __init__(self, adapters: List[SourceAdapter]):
        self.adapters = adapters

    def fetch_all(self) -> Dict[str, List[Story]]:
        result = {}
        for adapter in self.adapters:
            source = adapter.get_source_name()
            result[source] = adapter.fetch()
        return result

    def to_json_format(self, data: Dict[str, List[Story]]) -> Dict[str, Any]:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        generated = datetime.utcnow().isoformat() + 'Z'

        reddit_stories = []
        hn_stories = []

        for source, stories in data.items():
            for story in stories:
                story_dict = story.to_dict()
                if source == 'reddit':
                    reddit_stories.append(story_dict)
                elif source == 'hn':
                    hn_stories.append(story_dict)

        return {
            'v': 1,
            'd': today,
            'g': generated,
            'r': reddit_stories,
            'h': hn_stories
        }
