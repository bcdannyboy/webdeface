"""Screenshot capture and visual comparison capabilities."""

import asyncio
import hashlib
import io
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageChops, ImageStat
from playwright.async_api import Page

from ..config import get_settings
from ..utils.logging import get_structured_logger
from .types import ScrapingError

logger = get_structured_logger(__name__)


@dataclass
class VisualDiff:
    """Result of visual comparison between two screenshots."""

    similarity_score: float  # 0.0 to 1.0
    difference_percentage: float  # 0.0 to 100.0
    changed_regions: list[dict[str, int]]  # List of bounding boxes
    diff_image_data: Optional[bytes] = None
    has_significant_change: bool = False
    change_summary: str = ""


class ScreenshotCapture:
    """Handles screenshot capture with various options and optimizations."""

    def __init__(self):
        self.settings = get_settings().scraping
        self.default_viewport = {"width": 1920, "height": 1080}
        self.mobile_viewport = {"width": 375, "height": 667}

    async def capture_screenshot(
        self,
        page: Page,
        full_page: bool = True,
        viewport: Optional[dict[str, int]] = None,
        element_selector: Optional[str] = None,
        wait_for_selector: Optional[str] = None,
        hide_selectors: Optional[list[str]] = None,
    ) -> bytes:
        """Capture a screenshot of the page or specific element."""
        try:
            # Set viewport if specified
            if viewport:
                await page.set_viewport_size(viewport["width"], viewport["height"])

            # Wait for specific selector if specified
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=10000)

            # Hide elements if specified
            if hide_selectors:
                for selector in hide_selectors:
                    await page.add_style_tag(
                        content=f"{selector} {{ visibility: hidden !important; }}"
                    )

            # Wait for page to stabilize
            await page.wait_for_load_state("networkidle", timeout=5000)
            await asyncio.sleep(1)  # Additional stability wait

            # Capture screenshot
            screenshot_options = {
                "type": "png",
                "full_page": full_page,
                "timeout": 30000,
            }

            if element_selector:
                element = page.locator(element_selector)
                screenshot_data = await element.screenshot(**screenshot_options)
            else:
                screenshot_data = await page.screenshot(**screenshot_options)

            logger.debug(
                "Screenshot captured successfully",
                size=len(screenshot_data),
                full_page=full_page,
                element=element_selector,
            )

            return screenshot_data

        except Exception as e:
            logger.error(f"Screenshot capture failed: {str(e)}")
            raise ScrapingError(f"Screenshot capture failed: {str(e)}")

    async def capture_multiple_viewports(
        self, page: Page, viewports: Optional[list[dict[str, int]]] = None
    ) -> dict[str, bytes]:
        """Capture screenshots at multiple viewport sizes."""
        if viewports is None:
            viewports = [
                {"width": 1920, "height": 1080, "name": "desktop"},
                {"width": 1366, "height": 768, "name": "laptop"},
                {"width": 768, "height": 1024, "name": "tablet"},
                {"width": 375, "height": 667, "name": "mobile"},
            ]

        screenshots = {}

        for viewport in viewports:
            viewport_name = viewport.get(
                "name", f"{viewport['width']}x{viewport['height']}"
            )

            try:
                screenshot = await self.capture_screenshot(
                    page,
                    viewport={"width": viewport["width"], "height": viewport["height"]},
                    full_page=True,
                )
                screenshots[viewport_name] = screenshot

                logger.debug(f"Captured {viewport_name} screenshot")

            except Exception as e:
                logger.warning(
                    f"Failed to capture {viewport_name} screenshot: {str(e)}"
                )
                screenshots[viewport_name] = None

        return screenshots

    async def capture_with_scroll(
        self, page: Page, scroll_pause_time: float = 1.0, scroll_step: int = 500
    ) -> bytes:
        """Capture screenshot after scrolling through the page to trigger lazy loading."""
        try:
            # Get page height
            page_height = await page.evaluate("document.body.scrollHeight")
            viewport_height = await page.evaluate("window.innerHeight")

            # Scroll through the page
            current_scroll = 0
            while current_scroll < page_height:
                await page.evaluate(f"window.scrollTo(0, {current_scroll})")
                await asyncio.sleep(scroll_pause_time)
                current_scroll += scroll_step

            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(scroll_pause_time)

            # Capture final screenshot
            return await self.capture_screenshot(page, full_page=True)

        except Exception as e:
            logger.error(f"Scroll screenshot capture failed: {str(e)}")
            # Fallback to regular screenshot
            return await self.capture_screenshot(page, full_page=True)


class VisualComparator:
    """Compares screenshots and detects visual changes."""

    def __init__(self):
        self.similarity_threshold = 0.95
        self.significant_change_threshold = 0.8

    def compare_screenshots(
        self, screenshot1: bytes, screenshot2: bytes, sensitivity: float = 0.1
    ) -> VisualDiff:
        """Compare two screenshots and return visual differences."""
        try:
            # Load images
            img1 = Image.open(io.BytesIO(screenshot1))
            img2 = Image.open(io.BytesIO(screenshot2))

            # Ensure same size
            img1, img2 = self._normalize_images(img1, img2)

            # Calculate similarity
            similarity_score = self._calculate_similarity(img1, img2)

            # Generate difference image
            diff_img = ImageChops.difference(img1, img2)

            # Find changed regions
            changed_regions = self._find_changed_regions(diff_img, sensitivity)

            # Calculate difference percentage
            diff_percentage = (1.0 - similarity_score) * 100.0

            # Determine if change is significant
            has_significant_change = (
                similarity_score < self.significant_change_threshold
            )

            # Generate change summary
            change_summary = self._generate_change_summary(
                similarity_score, diff_percentage, len(changed_regions)
            )

            # Convert diff image to bytes
            diff_buffer = io.BytesIO()
            diff_img.save(diff_buffer, format="PNG")
            diff_image_data = diff_buffer.getvalue()

            logger.debug(
                "Visual comparison completed",
                similarity=similarity_score,
                diff_percentage=diff_percentage,
                changed_regions=len(changed_regions),
            )

            return VisualDiff(
                similarity_score=similarity_score,
                difference_percentage=diff_percentage,
                changed_regions=changed_regions,
                diff_image_data=diff_image_data,
                has_significant_change=has_significant_change,
                change_summary=change_summary,
            )

        except Exception as e:
            logger.error(f"Visual comparison failed: {str(e)}")
            raise ScrapingError(f"Visual comparison failed: {str(e)}")

    def _normalize_images(
        self, img1: Image.Image, img2: Image.Image
    ) -> tuple[Image.Image, Image.Image]:
        """Normalize images to the same size and format."""
        # Convert to RGB if needed
        if img1.mode != "RGB":
            img1 = img1.convert("RGB")
        if img2.mode != "RGB":
            img2 = img2.convert("RGB")

        # Resize to match dimensions
        if img1.size != img2.size:
            # Use the smaller dimensions
            width = min(img1.width, img2.width)
            height = min(img1.height, img2.height)

            img1 = img1.resize((width, height), Image.LANCZOS)
            img2 = img2.resize((width, height), Image.LANCZOS)

        return img1, img2

    def _calculate_similarity(self, img1: Image.Image, img2: Image.Image) -> float:
        """Calculate similarity score between two images."""
        # Method 1: Pixel-wise comparison
        diff = ImageChops.difference(img1, img2)
        stat = ImageStat.Stat(diff)

        # Calculate mean difference across all channels
        mean_diff = sum(stat.mean) / len(stat.mean)

        # Normalize to 0-1 scale (255 is max difference)
        pixel_similarity = 1.0 - (mean_diff / 255.0)

        # Method 2: Structural similarity using histograms
        hist1 = img1.histogram()
        hist2 = img2.histogram()

        # Calculate histogram correlation
        hist_correlation = self._calculate_histogram_correlation(hist1, hist2)

        # Combine both methods
        combined_similarity = (pixel_similarity * 0.7) + (hist_correlation * 0.3)

        return max(0.0, min(1.0, combined_similarity))

    def _calculate_histogram_correlation(
        self, hist1: list[int], hist2: list[int]
    ) -> float:
        """Calculate correlation between two histograms."""
        try:
            # Convert to numpy arrays
            h1 = np.array(hist1, dtype=np.float32)
            h2 = np.array(hist2, dtype=np.float32)

            # Normalize histograms
            h1 = h1 / (np.sum(h1) + 1e-10)
            h2 = h2 / (np.sum(h2) + 1e-10)

            # Calculate correlation coefficient
            correlation = np.corrcoef(h1, h2)[0, 1]

            # Handle NaN case
            if np.isnan(correlation):
                return 0.0

            return max(0.0, correlation)

        except Exception:
            return 0.0

    def _find_changed_regions(
        self, diff_img: Image.Image, sensitivity: float = 0.1
    ) -> list[dict[str, int]]:
        """Find regions with significant changes."""
        # Convert to grayscale for easier processing
        gray_diff = diff_img.convert("L")

        # Convert to numpy array
        diff_array = np.array(gray_diff)

        # Apply threshold to find significant changes
        threshold = int(255 * sensitivity)
        binary_diff = diff_array > threshold

        # Find connected components (changed regions)
        changed_regions = []

        try:
            # Simple connected component analysis
            labeled_regions = self._label_connected_components(binary_diff)

            for region_id in range(1, labeled_regions.max() + 1):
                region_mask = labeled_regions == region_id
                y_coords, x_coords = np.where(region_mask)

                if len(y_coords) > 100:  # Minimum region size
                    bbox = {
                        "x": int(x_coords.min()),
                        "y": int(y_coords.min()),
                        "width": int(x_coords.max() - x_coords.min()),
                        "height": int(y_coords.max() - y_coords.min()),
                        "area": len(y_coords),
                    }
                    changed_regions.append(bbox)

        except Exception as e:
            logger.debug(f"Region detection failed: {str(e)}")

        return changed_regions

    def _label_connected_components(self, binary_image: np.ndarray) -> np.ndarray:
        """Simple connected component labeling."""
        height, width = binary_image.shape
        labeled = np.zeros_like(binary_image, dtype=np.int32)
        current_label = 0

        # 4-connectivity neighbors
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for y in range(height):
            for x in range(width):
                if binary_image[y, x] and labeled[y, x] == 0:
                    current_label += 1
                    # Flood fill
                    stack = [(y, x)]
                    while stack:
                        cy, cx = stack.pop()
                        if labeled[cy, cx] != 0:
                            continue
                        labeled[cy, cx] = current_label

                        for dy, dx in neighbors:
                            ny, nx = cy + dy, cx + dx
                            if (
                                0 <= ny < height
                                and 0 <= nx < width
                                and binary_image[ny, nx]
                                and labeled[ny, nx] == 0
                            ):
                                stack.append((ny, nx))

        return labeled

    def _generate_change_summary(
        self, similarity: float, diff_percentage: float, region_count: int
    ) -> str:
        """Generate a human-readable summary of changes."""
        if similarity >= 0.99:
            return "No significant visual changes detected"
        elif similarity >= 0.95:
            return f"Minor visual changes detected ({diff_percentage:.1f}% difference)"
        elif similarity >= 0.8:
            return f"Moderate visual changes detected ({diff_percentage:.1f}% difference, {region_count} regions)"
        elif similarity >= 0.5:
            return f"Significant visual changes detected ({diff_percentage:.1f}% difference, {region_count} regions)"
        else:
            return f"Major visual changes detected ({diff_percentage:.1f}% difference, {region_count} regions)"


class VisualAnalyzer:
    """Advanced visual analysis and change detection."""

    def __init__(self):
        self.capture = ScreenshotCapture()
        self.comparator = VisualComparator()

    async def analyze_visual_changes(
        self,
        page: Page,
        baseline_screenshot: Optional[bytes] = None,
        capture_options: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Perform comprehensive visual analysis of a page."""
        analysis_result = {
            "screenshot_data": None,
            "visual_diff": None,
            "screenshot_hash": None,
            "analysis_timestamp": None,
            "capture_metadata": {},
        }

        try:
            # Set default capture options
            if capture_options is None:
                capture_options = {"full_page": True}

            # Capture current screenshot
            current_screenshot = await self.capture.capture_screenshot(
                page, **capture_options
            )

            analysis_result["screenshot_data"] = current_screenshot
            analysis_result["screenshot_hash"] = self._generate_screenshot_hash(
                current_screenshot
            )

            # Add capture metadata
            analysis_result["capture_metadata"] = {
                "screenshot_size": len(current_screenshot),
                "capture_options": capture_options,
                "page_url": page.url,
            }

            # Compare with baseline if provided
            if baseline_screenshot:
                visual_diff = self.comparator.compare_screenshots(
                    baseline_screenshot, current_screenshot
                )
                analysis_result["visual_diff"] = visual_diff

                logger.info(
                    "Visual analysis completed",
                    similarity=visual_diff.similarity_score,
                    has_change=visual_diff.has_significant_change,
                )

            return analysis_result

        except Exception as e:
            logger.error(f"Visual analysis failed: {str(e)}")
            raise ScrapingError(f"Visual analysis failed: {str(e)}")

    async def capture_comparison_set(
        self, page: Page, baseline_screenshots: dict[str, bytes]
    ) -> dict[str, VisualDiff]:
        """Capture screenshots and compare against a set of baselines."""
        comparisons = {}

        for viewport_name, baseline_data in baseline_screenshots.items():
            try:
                # Determine viewport from name
                viewport = self._get_viewport_from_name(viewport_name)

                # Capture current screenshot
                current_screenshot = await self.capture.capture_screenshot(
                    page, viewport=viewport, full_page=True
                )

                # Compare with baseline
                visual_diff = self.comparator.compare_screenshots(
                    baseline_data, current_screenshot
                )

                comparisons[viewport_name] = visual_diff

            except Exception as e:
                logger.warning(f"Comparison failed for {viewport_name}: {str(e)}")
                comparisons[viewport_name] = None

        return comparisons

    def _generate_screenshot_hash(self, screenshot_data: bytes) -> str:
        """Generate a hash of screenshot data."""
        return hashlib.blake2b(screenshot_data, digest_size=32).hexdigest()

    def _get_viewport_from_name(self, viewport_name: str) -> dict[str, int]:
        """Get viewport dimensions from name."""
        viewport_map = {
            "desktop": {"width": 1920, "height": 1080},
            "laptop": {"width": 1366, "height": 768},
            "tablet": {"width": 768, "height": 1024},
            "mobile": {"width": 375, "height": 667},
        }

        return viewport_map.get(viewport_name, {"width": 1920, "height": 1080})

    def calculate_visual_fingerprint(self, screenshot_data: bytes) -> dict[str, Any]:
        """Calculate a visual fingerprint for the screenshot."""
        try:
            img = Image.open(io.BytesIO(screenshot_data))

            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Calculate basic properties
            width, height = img.size

            # Calculate histogram features
            hist = img.histogram()

            # Split into R, G, B channels
            r_hist = hist[0:256]
            g_hist = hist[256:512]
            b_hist = hist[512:768]

            # Calculate statistical features
            fingerprint = {
                "width": width,
                "height": height,
                "aspect_ratio": width / height,
                "total_pixels": width * height,
                "r_mean": sum(i * v for i, v in enumerate(r_hist)) / sum(r_hist),
                "g_mean": sum(i * v for i, v in enumerate(g_hist)) / sum(g_hist),
                "b_mean": sum(i * v for i, v in enumerate(b_hist)) / sum(b_hist),
                "brightness": sum(r_hist[i] + g_hist[i] + b_hist[i] for i in range(256))
                / (3 * sum(r_hist)),
                "contrast": self._calculate_contrast(img),
                "dominant_colors": self._extract_dominant_colors(img),
            }

            return fingerprint

        except Exception as e:
            logger.error(f"Visual fingerprint calculation failed: {str(e)}")
            return {}

    def _calculate_contrast(self, img: Image.Image) -> float:
        """Calculate image contrast."""
        try:
            # Convert to grayscale
            gray = img.convert("L")
            # Calculate standard deviation as contrast measure
            stat = ImageStat.Stat(gray)
            return stat.stddev[0] / 255.0
        except Exception:
            return 0.0

    def _extract_dominant_colors(
        self, img: Image.Image, num_colors: int = 5
    ) -> list[tuple[int, int, int]]:
        """Extract dominant colors from image."""
        try:
            # Resize image for faster processing
            img_small = img.resize((150, 150))

            # Convert to palette with limited colors
            palette_img = img_small.quantize(colors=num_colors)

            # Get palette colors
            palette = palette_img.getpalette()

            # Extract RGB triplets
            colors = []
            for i in range(num_colors):
                r = palette[i * 3]
                g = palette[i * 3 + 1]
                b = palette[i * 3 + 2]
                colors.append((r, g, b))

            return colors

        except Exception:
            return []
