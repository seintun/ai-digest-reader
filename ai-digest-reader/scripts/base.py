from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Story:
    def __init__(self, story_id: str, title: str, url: str, score: int, comments: int, author: str):
        self.id = story_id
        self.title = title
        self.url = url
        self.score = score
        self.comments = comments
        self.author = author

    def to_dict(self) -> Dict[str, Any]:
        return {
            'i': self.id,
            't': self.title,
            'u': self.url,
            's': self.score,
            'c': self.comments,
            'a': self.author
        }


class SourceAdapter(ABC):
    @abstractmethod
    def fetch(self) -> List[Story]:
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        pass
