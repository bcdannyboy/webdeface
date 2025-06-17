"""Comprehensive API and external service mocking fixtures."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict

from tests.mock_settings import create_mock_settings


@pytest.fixture(scope="function")
def mock_claude_api():
    """Mock Claude API to prevent real external calls."""
    with patch("src.webdeface.classifier.claude.AsyncAnthropic") as mock_anthropic:
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        
        # Standard successful response
        mock_response = Mock()
        mock_response.content = [Mock(text='{"classification": "benign", "confidence": 0.8, "reasoning": "Test response"}')]
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        yield mock_client


@pytest.fixture(scope="function")
def mock_external_http():
    """Mock all external HTTP requests."""
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html><body>Test content</body></html>")
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.post = AsyncMock(return_value=mock_response)
        
        yield mock_session


@pytest.fixture(scope="function")
def comprehensive_api_mocks(mock_claude_api, mock_external_http):
    """Comprehensive mocking of all external APIs and services."""
    mock_settings = create_mock_settings()
    
    patches = [
        # Settings mocking for all import paths
        patch("src.webdeface.config.settings.get_settings", return_value=mock_settings),
        patch("src.webdeface.config.get_settings", return_value=mock_settings),
        patch("src.webdeface.api.auth.get_settings", return_value=mock_settings),
        
        # Authentication mocking
        patch("src.webdeface.api.auth.verify_api_token", return_value=True),
        
        # Storage mocking
        patch("src.webdeface.storage.get_storage_manager"),
        patch("src.webdeface.storage.sqlite.database.create_async_engine"),
        patch("src.webdeface.storage.qdrant.client.AsyncQdrantClient"),
        
        # Scheduler and orchestrator mocking
        patch("src.webdeface.scheduler.orchestrator.get_scheduling_orchestrator"),
        patch("src.webdeface.scheduler.manager.SchedulerManager"),
        
        # Browser automation mocking
        patch("src.webdeface.scraper.browser.async_playwright"),
        
        # ML/AI model mocking
        patch("src.webdeface.classifier.vectorizer.SentenceTransformer"),
        
        # Slack integration mocking
        patch("slack_bolt.async_app.AsyncApp"),
        
        # File system mocking for configs
        patch("builtins.open", side_effect=FileNotFoundError("Test mode - no config file")),
    ]
    
    with patch.multiple(
        "src.webdeface.classifier.claude",
        AsyncAnthropic=lambda **kwargs: mock_claude_api,
        get_claude_client=AsyncMock(return_value=Mock(
            classify_content=AsyncMock(),
            validate_api_connection=AsyncMock(return_value=True)
        ))
    ):
        yield {
            "settings": mock_settings,
            "claude_client": mock_claude_api,
            "http_session": mock_external_http,
        }


@pytest.fixture(scope="function") 
def mock_auth_token_verification():
    """Mock authentication token verification to always succeed with test token."""
    def verify_token(token: str) -> bool:
        return token in ["test-token-123", "Bearer test-token-123"]
    
    with patch("src.webdeface.api.auth.verify_api_token", side_effect=verify_token):
        yield verify_token


@pytest.fixture(scope="function")
def prevent_external_calls():
    """Fixture that actively prevents any external network calls."""
    
    def block_external_call(*args, **kwargs):
        raise RuntimeError("External network call blocked in test environment")
    
    patches = [
        # Block common HTTP libraries
        patch("aiohttp.ClientSession.get", side_effect=block_external_call),
        patch("aiohttp.ClientSession.post", side_effect=block_external_call),
        patch("requests.get", side_effect=block_external_call),
        patch("requests.post", side_effect=block_external_call),
        patch("urllib.request.urlopen", side_effect=block_external_call),
        
        # Block Claude API specifically
        patch("anthropic.AsyncAnthropic.messages.create", side_effect=block_external_call),
        
        # Block other AI services
        patch("openai.ChatCompletion.create", side_effect=block_external_call),
    ]
    
    with patch.multiple("src.webdeface.classifier.claude", **{
        "AsyncAnthropic": Mock(side_effect=block_external_call)
    }):
        for p in patches:
            p.start()
        
        yield
        
        for p in patches:
            p.stop()