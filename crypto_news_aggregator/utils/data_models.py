# crypto_news_aggregator/utils/data_models.py
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime

class Article(BaseModel):
    title: str
    link: HttpUrl
    published_at: datetime
    source_name: str
    content_snippet: Optional[str] = None # Summary or short description
    related_coins: List[str] = Field(default_factory=list) # List of tickers like ["BTC", "ETH"]

    class Config:
        # Allow arbitrary types for datetime, as feedparser might return non-standard datetime objects
        # We handle conversion in the source modules
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def __hash__(self):
        # For use in sets for deduplication
        return hash((self.title, self.link))

    def __eq__(self, other):
        if not isinstance(other, Article):
            return NotImplemented
        return (self.title, self.link) == (other.title, other.link)