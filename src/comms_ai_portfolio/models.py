from dataclasses import dataclass


@dataclass
class Article:
    title: str
    body: str
    source: str
    url: str
    published_at: str


@dataclass
class Event:
    event_id: str
    summary: str
    source: str
    timestamp: str
