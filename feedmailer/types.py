
from dataclasses import dataclass 
from typing import Optional, TypedDict
from datetime import datetime

@dataclass 
class Article:
    title: str
    url: str
    author: Optional[str]
    feed_id: int
    category: Optional[str]
    description: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

@dataclass
class Feed:
    feed_id: int
    title: str
    created_at: datetime
    refreshed_at: Optional[datetime]
    updated_at: Optional[datetime]
    url: str

class FeedsFilter(TypedDict):
    feed_id: Optional[int]
    title: Optional[str]
    url: Optional[str]


class NewSubscription(TypedDict):
    title: str
    url: str
    email: str
    digest: bool
    desc_length: Optional[int]

class NewArticle(TypedDict):
    url: str
    title: str
    author: Optional[str]
    feed_id: int
    description: Optional[str]
    published_at: Optional[datetime]

@dataclass
class Subscription:
    subscription_id: int
    desc_length: Optional[int]
    email: str
    feed_id: int
    digest: bool
    attempted_delivery_at: Optional[datetime]
    title: str
    url: str
    created_at: datetime
    updated_at: Optional[datetime]
    refreshed_at: Optional[datetime]

class SubscriptionsFilter(TypedDict):
    subscription_id: Optional[int]
    title: Optional[str]
    url: Optional[str]
