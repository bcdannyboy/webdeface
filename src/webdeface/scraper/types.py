"""Type definitions for the scraper module."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class ScrapingError(Exception):
    """Base exception for scraping-related errors."""

    pass


@dataclass
class PageResult:
    """Result of scraping a single page."""

    url: str
    html: str
    dom_outline: str
    text_blocks: list[str]
    title: Optional[str] = None
    meta_description: Optional[str] = None
    status_code: int = 200
    scraped_at: datetime = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow()


@dataclass
class CrawlResult:
    """Result of crawling multiple pages from a site."""

    base_url: str
    pages: list[PageResult]
    errors: list[str]
    total_pages: int
    successful_pages: int
    crawl_duration: float
    crawled_at: datetime = None

    def __post_init__(self):
        if self.crawled_at is None:
            self.crawled_at = datetime.utcnow()

        self.total_pages = len(self.pages)
        self.successful_pages = len([p for p in self.pages if p.status_code == 200])
