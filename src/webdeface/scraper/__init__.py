"""Web scraping module for the Web Defacement Monitor.

This module provides comprehensive web scraping capabilities including:
- Playwright browser automation with stealth configuration
- Content extraction and preprocessing
- Visual analysis and screenshot comparison
- Content hashing and change detection
- Orchestrated scraping with error handling and monitoring
"""

from .browser import (
    BrowserManager,
    BrowserPool,
    StealthBrowser,
    cleanup_browser_pool,
    get_browser_pool,
)
from .extractor import ContentExtractor, ContentProcessor
from .hashing import (
    ChangeDetectionResult,
    ChangeDetector,
    ContentHash,
    ContentHasher,
    get_hash_store,
)
from .orchestrator import (
    ScrapingJob,
    ScrapingOrchestrator,
    ScrapingQueue,
    ScrapingResult,
    ScrapingWorker,
    cleanup_scraping_orchestrator,
    get_scraping_orchestrator,
)
from .types import CrawlResult, PageResult, ScrapingError
from .visual import ScreenshotCapture, VisualAnalyzer, VisualComparator, VisualDiff

__all__ = [
    # Types
    "ScrapingError",
    "PageResult",
    "CrawlResult",
    "VisualDiff",
    "ContentHash",
    "ChangeDetectionResult",
    "ScrapingJob",
    "ScrapingResult",
    # Browser automation
    "StealthBrowser",
    "BrowserPool",
    "BrowserManager",
    "get_browser_pool",
    "cleanup_browser_pool",
    # Content extraction
    "ContentExtractor",
    "ContentProcessor",
    # Visual analysis
    "ScreenshotCapture",
    "VisualComparator",
    "VisualAnalyzer",
    # Change detection
    "ContentHasher",
    "ChangeDetector",
    "get_hash_store",
    # Orchestration
    "ScrapingOrchestrator",
    "ScrapingQueue",
    "ScrapingWorker",
    "get_scraping_orchestrator",
    "cleanup_scraping_orchestrator",
]
