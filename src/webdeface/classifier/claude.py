"""Claude AI client with specialized defacement detection prompts."""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from anthropic import AsyncAnthropic

from ..config import get_settings
from ..utils.logging import get_structured_logger
from .types import Classification, ClassificationError, ClassificationResult

logger = get_structured_logger(__name__)


@dataclass
class DefacementPrompt:
    """Structured prompt for defacement detection."""

    system_prompt: str
    user_prompt_template: str
    response_format: str
    confidence_instructions: str


class DefacementPromptLibrary:
    """Library of specialized prompts for different defacement detection scenarios."""

    def __init__(self):
        self.prompts = self._initialize_prompts()

    def _initialize_prompts(self) -> dict[str, DefacementPrompt]:
        """Initialize the prompt library."""
        return {
            "general_analysis": DefacementPrompt(
                system_prompt="""You are a cybersecurity expert specializing in website defacement detection. Your task is to analyze website content changes and determine if they indicate a potential defacement or malicious modification.

A website defacement typically involves:
- Unauthorized modification of content by attackers
- Injection of malicious messages, political statements, or propaganda
- Replacement of legitimate content with attacker-controlled content
- Addition of inappropriate images, videos, or links
- Vandalism or graffiti-style messages
- Cryptocurrency mining scripts or malware injection
- Phishing attempts or scam content

You should distinguish defacements from legitimate changes such as:
- Normal content updates and news articles
- Scheduled maintenance messages
- Regular business updates
- Seasonal content changes
- Marketing campaigns
- Software updates and feature announcements

Analyze the provided content carefully and respond with structured JSON.""",
                user_prompt_template="""Please analyze the following website content for potential defacement:

WEBSITE URL: {url}
WEBSITE CONTEXT: {site_context}

CHANGED CONTENT:
{changed_content}

STATIC CONTEXT (unchanged content for reference):
{static_context}

PREVIOUS CLASSIFICATION (if any): {previous_classification}

Please analyze this content and respond with a JSON object containing:
{{
    "classification": "benign|defacement|unclear",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation of your analysis",
    "risk_indicators": ["list", "of", "specific", "risk", "indicators"],
    "benign_indicators": ["list", "of", "indicators", "suggesting", "legitimate", "change"],
    "recommended_action": "monitor|alert|investigate|ignore",
    "severity": "low|medium|high|critical"
}}""",
                response_format="json",
                confidence_instructions="Provide confidence as a float between 0.0 and 1.0, where 1.0 means absolutely certain.",
            ),
            "content_injection": DefacementPrompt(
                system_prompt="""You are analyzing website content specifically for signs of content injection attacks. Focus on:

MALICIOUS INJECTION INDICATORS:
- Unexpected JavaScript code or script tags
- Suspicious iframe elements pointing to external domains
- Cryptocurrency mining code (e.g., Coinhive, Monero miners)
- Redirection scripts to malicious sites
- Base64 encoded content that could hide malicious payloads
- Unusual external resource loading
- Suspicious form submissions to external domains

LEGITIMATE CODE PATTERNS:
- Analytics tracking (Google Analytics, Facebook Pixel, etc.)
- CDN resources from known providers
- Legitimate advertising networks
- Standard social media widgets
- Known payment processors
- Established third-party services

Analyze the technical aspects of content changes to identify potential injection attacks.""",
                user_prompt_template="""Analyze this content for potential code injection or malicious script insertion:

WEBSITE: {url}
TECHNICAL CONTEXT: {site_context}

NEW/CHANGED CODE:
{changed_content}

EXISTING CODE CONTEXT:
{static_context}

Focus on technical indicators of malicious injection. Respond with JSON analysis.""",
                response_format="json",
                confidence_instructions="Base confidence on technical evidence of malicious patterns.",
            ),
            "visual_defacement": DefacementPrompt(
                system_prompt="""You are analyzing visual changes to detect website defacement. Focus on:

VISUAL DEFACEMENT INDICATORS:
- Unauthorized messages or text overlays
- Political or ideological content not matching site purpose
- Hate speech, offensive imagery, or inappropriate content
- "Hacked by" messages or hacker signatures
- Replaced logos or branding with attacker content
- Vandalism-style modifications
- Unexpected pop-ups or modal dialogs
- Content in wrong languages for the target audience

LEGITIMATE VISUAL CHANGES:
- Seasonal updates and holiday themes
- New product announcements
- Marketing campaign updates
- Rebranding efforts
- User interface improvements
- Content management system updates

Analyze visual content descriptions and changes for signs of unauthorized modification.""",
                user_prompt_template="""Analyze these visual changes for potential defacement:

WEBSITE: {url}
VISUAL CONTEXT: {site_context}

VISUAL CHANGES DETECTED:
{changed_content}

BASELINE VISUAL CONTEXT:
{static_context}

Analyze whether these visual changes indicate defacement or legitimate updates.""",
                response_format="json",
                confidence_instructions="Consider the context and nature of visual changes in confidence assessment.",
            ),
        }

    def get_prompt(self, prompt_type: str = "general_analysis") -> DefacementPrompt:
        """Get a prompt by type."""
        return self.prompts.get(prompt_type, self.prompts["general_analysis"])

    def list_available_prompts(self) -> list[str]:
        """List available prompt types."""
        return list(self.prompts.keys())


class ClaudeClient:
    """Async Claude AI client for defacement detection."""

    def __init__(self):
        self.settings = get_settings().claude
        self.client: Optional[AsyncAnthropic] = None
        self.prompt_library = DefacementPromptLibrary()
        self._rate_limiter = asyncio.Semaphore(5)  # Max 5 concurrent requests
        self._last_request_time = 0.0
        self._min_request_interval = 0.2  # Minimum 200ms between requests

    async def _ensure_client(self) -> None:
        """Ensure the Claude client is initialized."""
        if self.client is None:
            self.client = AsyncAnthropic(
                api_key=self.settings.api_key.get_secret_value()
            )

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)

        self._last_request_time = asyncio.get_event_loop().time()

    async def classify_content(
        self,
        changed_content: list[str],
        static_context: list[str],
        site_url: str,
        site_context: Optional[dict[str, Any]] = None,
        prompt_type: str = "general_analysis",
        previous_classification: Optional[ClassificationResult] = None,
    ) -> ClassificationResult:
        """Classify content using Claude AI."""
        async with self._rate_limiter:
            await self._rate_limit()
            await self._ensure_client()

            try:
                # Prepare prompt
                prompt = self.prompt_library.get_prompt(prompt_type)

                # Format content
                changed_text = (
                    "\n\n".join(changed_content)
                    if changed_content
                    else "No content changes detected"
                )
                static_text = (
                    "\n\n".join(static_context[:5])
                    if static_context
                    else "No context available"
                )  # Limit context

                # Prepare context
                context_str = (
                    json.dumps(site_context)
                    if site_context
                    else "No additional context"
                )
                prev_classification_str = (
                    f"Previous: {previous_classification.label.value} (confidence: {previous_classification.confidence})"
                    if previous_classification
                    else "None"
                )

                # Format user prompt
                user_prompt = prompt.user_prompt_template.format(
                    url=site_url,
                    site_context=context_str,
                    changed_content=changed_text,
                    static_context=static_text,
                    previous_classification=prev_classification_str,
                )

                # Truncate if too long (Claude has token limits)
                if len(user_prompt) > 50000:  # Conservative limit
                    user_prompt = (
                        user_prompt[:50000] + "\n\n[Content truncated due to length]"
                    )

                logger.debug(
                    "Sending classification request to Claude",
                    url=site_url,
                    prompt_type=prompt_type,
                    content_length=len(changed_text),
                )

                # Send request to Claude
                response = await self.client.messages.create(
                    model=self.settings.model,
                    max_tokens=self.settings.max_tokens,
                    temperature=self.settings.temperature,
                    system=prompt.system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )

                # Parse response
                result = await self._parse_classification_response(
                    response, site_url, prompt_type
                )

                logger.info(
                    "Content classification completed",
                    url=site_url,
                    classification=result.label.value,
                    confidence=result.confidence,
                    tokens_used=response.usage.input_tokens
                    + response.usage.output_tokens,
                )

                return result

            except Exception as e:
                logger.error(f"Claude classification failed for {site_url}: {str(e)}")
                raise ClassificationError(f"Classification failed: {str(e)}")

    async def _parse_classification_response(
        self, response: Any, site_url: str, prompt_type: str
    ) -> ClassificationResult:
        """Parse Claude's response into a ClassificationResult."""
        try:
            # Extract text from response
            response_text = response.content[0].text

            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_content = response_text[json_start:json_end]
                parsed_response = json.loads(json_content)
            else:
                # Fallback: treat entire response as explanation
                parsed_response = {
                    "classification": "unclear",
                    "confidence": 0.5,
                    "reasoning": response_text,
                    "risk_indicators": [],
                    "benign_indicators": [],
                    "recommended_action": "investigate",
                    "severity": "medium",
                }

            # Validate and normalize classification
            classification_str = parsed_response.get(
                "classification", "unclear"
            ).lower()
            if classification_str in ["benign", "defacement", "unclear"]:
                classification = Classification(classification_str)
            else:
                classification = Classification.UNCLEAR

            # Validate confidence
            confidence = float(parsed_response.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            # Extract explanation
            explanation = parsed_response.get("reasoning", "No explanation provided")

            # Build reasoning with additional details
            reasoning_parts = [explanation]

            risk_indicators = parsed_response.get("risk_indicators", [])
            if risk_indicators:
                reasoning_parts.append(f"Risk indicators: {', '.join(risk_indicators)}")

            benign_indicators = parsed_response.get("benign_indicators", [])
            if benign_indicators:
                reasoning_parts.append(
                    f"Benign indicators: {', '.join(benign_indicators)}"
                )

            recommended_action = parsed_response.get("recommended_action", "monitor")
            reasoning_parts.append(f"Recommended action: {recommended_action}")

            severity = parsed_response.get("severity", "medium")
            reasoning_parts.append(f"Severity: {severity}")

            full_reasoning = "\n\n".join(reasoning_parts)

            # Create result
            result = ClassificationResult(
                label=classification,
                explanation=explanation,
                confidence=confidence,
                reasoning=full_reasoning,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                model_used=self.settings.model,
                classified_at=datetime.utcnow(),
            )

            return result

        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse JSON response from Claude for {site_url}: {str(e)}"
            )
            # Create fallback result
            return ClassificationResult(
                label=Classification.UNCLEAR,
                explanation="Failed to parse AI response",
                confidence=0.3,
                reasoning=f"JSON parsing error: {str(e)}. Raw response: {response.content[0].text[:500]}",
                tokens_used=getattr(response.usage, "input_tokens", 0)
                + getattr(response.usage, "output_tokens", 0),
                model_used=self.settings.model,
                classified_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error parsing Claude response for {site_url}: {str(e)}")
            raise ClassificationError(f"Response parsing failed: {str(e)}")

    async def batch_classify(
        self, requests: list[dict[str, Any]], max_concurrent: int = 3
    ) -> list[ClassificationResult]:
        """Classify multiple content samples concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def classify_single(request_data: dict[str, Any]) -> ClassificationResult:
            async with semaphore:
                return await self.classify_content(**request_data)

        # Execute all requests
        tasks = [classify_single(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Batch classification failed for request {i}: {str(result)}"
                )
                processed_results.append(
                    ClassificationResult(
                        label=Classification.UNCLEAR,
                        explanation="Batch processing error",
                        confidence=0.0,
                        reasoning=f"Error: {str(result)}",
                        classified_at=datetime.utcnow(),
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def validate_api_connection(self) -> bool:
        """Validate connection to Claude API."""
        try:
            await self._ensure_client()

            # Send a simple test request
            response = await self.client.messages.create(
                model=self.settings.model,
                max_tokens=10,
                temperature=0.1,
                system="You are a test assistant.",
                messages=[
                    {
                        "role": "user",
                        "content": "Respond with 'OK' if you can see this message.",
                    }
                ],
            )

            return "ok" in response.content[0].text.lower()

        except Exception as e:
            logger.error(f"Claude API validation failed: {str(e)}")
            return False

    def get_usage_stats(self) -> dict[str, Any]:
        """Get usage statistics (placeholder for future implementation)."""
        return {
            "client_initialized": self.client is not None,
            "model": self.settings.model,
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
            "available_prompts": self.prompt_library.list_available_prompts(),
        }


# Global Claude client instance
_claude_client: Optional[ClaudeClient] = None


async def get_claude_client() -> ClaudeClient:
    """Get or create the global Claude client."""
    global _claude_client

    if _claude_client is None:
        _claude_client = ClaudeClient()

    return _claude_client


def cleanup_claude_client() -> None:
    """Clean up the global Claude client."""
    global _claude_client
    _claude_client = None
