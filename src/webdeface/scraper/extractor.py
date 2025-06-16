"""Website content extraction and preprocessing pipeline."""

import hashlib
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag
from playwright.async_api import Page

from ..utils.logging import get_structured_logger
from .types import ScrapingError

logger = get_structured_logger(__name__)


class ContentExtractor:
    """Extracts and preprocesses website content from HTML."""

    def __init__(self):
        self.text_block_min_length = 10
        self.significant_tags = {
            "title",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "div",
            "span",
            "article",
            "section",
            "main",
            "nav",
            "header",
            "footer",
            "aside",
            "blockquote",
        }
        self.ignore_tags = {
            "script",
            "style",
            "noscript",
            "meta",
            "link",
            "head",
            "comment",
            "svg",
            "path",
        }

    async def extract_from_page(self, page: Page, url: str) -> dict[str, any]:
        """Extract content from a Playwright page."""
        try:
            # Get page content
            html = await page.content()
            title = await page.title()

            # Extract metadata
            meta_description = await page.locator(
                'meta[name="description"]'
            ).get_attribute("content")
            if not meta_description:
                meta_description = await page.locator(
                    'meta[property="og:description"]'
                ).get_attribute("content")

            # Extract structured content
            content_data = self.extract_from_html(html, url)
            content_data["title"] = title
            content_data["meta_description"] = meta_description

            logger.debug(
                f"Extracted content from {url}",
                text_blocks=len(content_data["text_blocks"]),
                dom_elements=len(content_data["dom_outline"]),
            )

            return content_data

        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {str(e)}")
            raise ScrapingError(f"Content extraction failed: {str(e)}")

    def extract_from_html(self, html: str, base_url: str) -> dict[str, any]:
        """Extract structured content from HTML string."""
        soup = self._get_soup(html)

        # Remove unwanted elements
        self._clean_soup(soup)

        # Extract different content types
        text_blocks = self._extract_text_blocks(soup)
        dom_outline = self._extract_dom_outline(soup)
        links = self._extract_links(soup, base_url)
        images = self._extract_images(soup, base_url)
        forms = self._extract_forms(soup)

        # Generate content fingerprints
        main_content = self._extract_main_content(soup)
        content_hash = self._generate_content_hash(main_content)
        structure_hash = self._generate_structure_hash(dom_outline)

        return {
            "html": str(soup),
            "text_blocks": text_blocks,
            "dom_outline": dom_outline,
            "links": links,
            "images": images,
            "forms": forms,
            "main_content": main_content,
            "content_hash": content_hash,
            "structure_hash": structure_hash,
            "word_count": sum(len(block.split()) for block in text_blocks),
            "character_count": sum(len(block) for block in text_blocks),
        }

    def _get_soup(self, html: str) -> BeautifulSoup:
        """Create BeautifulSoup object from HTML string."""
        return BeautifulSoup(html, "html.parser")

    def _clean_soup(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from soup."""
        # Remove script and style elements
        for tag in soup.find_all(self.ignore_tags):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, type(soup))):
            comment.extract()

        # Remove hidden elements
        for tag in soup.find_all(
            attrs={"style": re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden")}
        ):
            tag.decompose()

        # Remove elements with aria-hidden
        for tag in soup.find_all(attrs={"aria-hidden": "true"}):
            tag.decompose()

    def _extract_text_blocks(self, soup: BeautifulSoup) -> list[str]:
        """Extract meaningful text blocks from the soup."""
        text_blocks = []

        # Extract text from significant tags
        for tag_name in self.significant_tags:
            tags = soup.find_all(tag_name)
            for tag in tags:
                text = self._get_clean_text(tag)
                if len(text) >= self.text_block_min_length:
                    text_blocks.append(text)

        # Remove duplicates while preserving order
        seen = set()
        unique_blocks = []
        for block in text_blocks:
            if block not in seen:
                seen.add(block)
                unique_blocks.append(block)

        return unique_blocks

    def _extract_dom_outline(self, soup: BeautifulSoup) -> list[dict[str, any]]:
        """Extract DOM structure outline."""
        outline = []

        def traverse_element(element, depth=0):
            if isinstance(element, Tag):
                # Skip ignored tags
                if element.name in self.ignore_tags:
                    return

                element_info = {
                    "tag": element.name,
                    "depth": depth,
                    "classes": element.get("class", []),
                    "id": element.get("id"),
                    "text_length": len(self._get_clean_text(element)),
                    "child_count": len(list(element.children)),
                }

                # Add attributes for important elements
                if element.name in ["a", "img", "form", "input", "button"]:
                    element_info["attributes"] = dict(element.attrs)

                outline.append(element_info)

                # Recursively process children (limit depth to avoid excessive nesting)
                if depth < 10:
                    for child in element.children:
                        traverse_element(child, depth + 1)

        # Start traversal from body or root
        body = soup.find("body") or soup
        traverse_element(body)

        return outline

    def _extract_links(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[dict[str, str]]:
        """Extract all links from the page."""
        links = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            if href and not href.startswith("#"):
                absolute_url = urljoin(base_url, href)
                link_text = self._get_clean_text(link)

                links.append(
                    {
                        "url": absolute_url,
                        "text": link_text,
                        "title": link.get("title", ""),
                        "is_external": self._is_external_link(absolute_url, base_url),
                    }
                )

        return links

    def _extract_images(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[dict[str, str]]:
        """Extract all images from the page."""
        images = []

        for img in soup.find_all("img", src=True):
            src = img["src"].strip()
            if src:
                absolute_url = urljoin(base_url, src)

                images.append(
                    {
                        "url": absolute_url,
                        "alt": img.get("alt", ""),
                        "title": img.get("title", ""),
                        "width": img.get("width", ""),
                        "height": img.get("height", ""),
                    }
                )

        return images

    def _extract_forms(self, soup: BeautifulSoup) -> list[dict[str, any]]:
        """Extract form information from the page."""
        forms = []

        for form in soup.find_all("form"):
            form_info = {
                "action": form.get("action", ""),
                "method": form.get("method", "get").lower(),
                "inputs": [],
            }

            # Extract form inputs
            for input_elem in form.find_all(["input", "textarea", "select"]):
                input_info = {
                    "type": input_elem.get("type", "text"),
                    "name": input_elem.get("name", ""),
                    "id": input_elem.get("id", ""),
                    "placeholder": input_elem.get("placeholder", ""),
                    "required": input_elem.has_attr("required"),
                }
                form_info["inputs"].append(input_info)

            forms.append(form_info)

        return forms

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content area of the page."""
        # Try to find main content containers
        main_selectors = [
            "main",
            '[role="main"]',
            "#main",
            ".main",
            "#content",
            ".content",
            ".post-content",
            "article",
            ".article",
            "#article",
        ]

        for selector in main_selectors:
            element = soup.select_one(selector)
            if element:
                return self._get_clean_text(element)

        # Fallback: extract from body, excluding header/footer/nav
        body = soup.find("body")
        if body:
            # Remove common non-content areas
            for tag in body.find_all(["header", "footer", "nav", "aside"]):
                tag.decompose()

            return self._get_clean_text(body)

        # Final fallback: all text
        return self._get_clean_text(soup)

    def _get_clean_text(self, element) -> str:
        """Extract clean text from an element."""
        if isinstance(element, NavigableString):
            return str(element).strip()

        if isinstance(element, Tag):
            # Get text and clean whitespace
            text = element.get_text(separator=" ", strip=True)
            # Normalize whitespace
            text = re.sub(r"\s+", " ", text)
            return text.strip()

        return str(element).strip()

    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash of the main content."""
        # Normalize content for consistent hashing
        normalized = re.sub(r"\s+", " ", content.lower().strip())
        return hashlib.blake2b(normalized.encode("utf-8"), digest_size=32).hexdigest()

    def _generate_structure_hash(self, dom_outline: list[dict]) -> str:
        """Generate a hash of the DOM structure."""
        # Create a simplified structure representation
        structure_repr = []
        for element in dom_outline:
            repr_str = (
                f"{element['tag']}:{element['depth']}:{len(element.get('classes', []))}"
            )
            structure_repr.append(repr_str)

        structure_string = "|".join(structure_repr)
        return hashlib.blake2b(
            structure_string.encode("utf-8"), digest_size=16
        ).hexdigest()

    def _is_external_link(self, url: str, base_url: str) -> bool:
        """Check if a URL is external to the base domain."""
        try:
            base_domain = urlparse(base_url).netloc
            link_domain = urlparse(url).netloc
            return link_domain != base_domain and link_domain != ""
        except Exception:
            return True


class ContentProcessor:
    """Processes extracted content for analysis and comparison."""

    def __init__(self):
        self.stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
        }

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase
        text = text.lower()

        # Remove special characters and normalize whitespace
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def extract_keywords(self, text: str, min_length: int = 3) -> list[str]:
        """Extract keywords from text."""
        normalized = self.normalize_text(text)
        words = normalized.split()

        # Filter out stopwords and short words
        keywords = [
            word
            for word in words
            if len(word) >= min_length and word not in self.stopwords
        ]

        return keywords

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using improved similarity measure."""
        if not text1 or not text2:
            return 0.0

        # Extract keywords from both texts
        keywords1 = set(self.extract_keywords(text1))
        keywords2 = set(self.extract_keywords(text2))

        if not keywords1 and not keywords2:
            return 1.0

        if not keywords1 or not keywords2:
            return 0.0

        # Calculate intersection and sizes
        intersection = len(keywords1.intersection(keywords2))
        min_size = min(len(keywords1), len(keywords2))
        max_size = max(len(keywords1), len(keywords2))
        union = len(keywords1.union(keywords2))

        # Multiple similarity measures for robust comparison
        jaccard_similarity = intersection / union if union > 0 else 0.0
        overlap_coefficient = intersection / min_size if min_size > 0 else 0.0
        dice_coefficient = (
            (2 * intersection) / (len(keywords1) + len(keywords2))
            if (len(keywords1) + len(keywords2)) > 0
            else 0.0
        )

        # Base similarity using weighted combination
        base_similarity = (
            (jaccard_similarity * 0.2)
            + (overlap_coefficient * 0.6)
            + (dice_coefficient * 0.2)
        )

        # Apply bonus for substantial overlap (50% or more of smaller set)
        overlap_ratio = intersection / min_size if min_size > 0 else 0.0
        if overlap_ratio >= 0.5:
            # Bonus scaling based on overlap strength
            bonus = min(0.15, overlap_ratio * 0.2)
            base_similarity += bonus

        return min(1.0, base_similarity)

    def detect_significant_changes(
        self,
        old_content: dict[str, any],
        new_content: dict[str, any],
        threshold: float = 0.3,
    ) -> dict[str, any]:
        """Detect significant changes between two content extractions."""
        changes = {
            "content_similarity": 0.0,
            "structure_similarity": 0.0,
            "title_changed": False,
            "significant_change": False,
            "change_summary": [],
        }

        # Compare main content
        if old_content.get("main_content") and new_content.get("main_content"):
            changes["content_similarity"] = self.calculate_text_similarity(
                old_content["main_content"], new_content["main_content"]
            )

        # Compare DOM structure
        if old_content.get("structure_hash") and new_content.get("structure_hash"):
            changes["structure_similarity"] = (
                1.0
                if old_content["structure_hash"] == new_content["structure_hash"]
                else 0.0
            )

        # Check title changes
        old_title = old_content.get("title", "")
        new_title = new_content.get("title", "")
        changes["title_changed"] = old_title != new_title

        # Detect significant changes
        content_changed = changes["content_similarity"] < (1.0 - threshold)
        structure_changed = changes["structure_similarity"] < 0.5

        changes["significant_change"] = (
            content_changed or structure_changed or changes["title_changed"]
        )

        # Generate change summary
        if changes["title_changed"]:
            changes["change_summary"].append("Title changed")

        if content_changed:
            changes["change_summary"].append(
                f'Content similarity: {changes["content_similarity"]:.2f}'
            )

        if structure_changed:
            changes["change_summary"].append("DOM structure changed")

        # Word count changes
        old_words = old_content.get("word_count", 0)
        new_words = new_content.get("word_count", 0)
        if abs(old_words - new_words) > 50:  # Significant word count change
            changes["change_summary"].append(
                f"Word count changed: {old_words} → {new_words}"
            )

        return changes

    def extract_text_features(self, content: dict[str, any]) -> dict[str, any]:
        """Extract features from content for ML analysis."""
        features = {
            "word_count": content.get("word_count", 0),
            "character_count": content.get("character_count", 0),
            "text_block_count": len(content.get("text_blocks", [])),
            "link_count": len(content.get("links", [])),
            "external_link_count": len(
                [
                    link
                    for link in content.get("links", [])
                    if link.get("is_external", False)
                ]
            ),
            "image_count": len(content.get("images", [])),
            "form_count": len(content.get("forms", [])),
            "dom_depth": max(
                (elem.get("depth", 0) for elem in content.get("dom_outline", [])),
                default=0,
            ),
            "has_main_content": bool(content.get("main_content")),
            "title_length": len(content.get("title", "")),
            "meta_description_length": len(content.get("meta_description", "") or ""),
        }

        # Calculate ratios
        if features["word_count"] > 0:
            features["links_per_word"] = features["link_count"] / features["word_count"]
            features["images_per_word"] = (
                features["image_count"] / features["word_count"]
            )
        else:
            features["links_per_word"] = 0.0
            features["images_per_word"] = 0.0

        return features
