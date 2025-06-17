"""Test to validate that authentication mocking is working correctly."""

import pytest
from unittest.mock import patch, Mock
from src.webdeface.api.auth import verify_api_token
from tests.mock_settings import create_mock_settings


class TestAuthenticationMocking:
    """Test authentication mocking to ensure no external calls."""

    def test_auth_verification_with_mock_settings(self):
        """Test that auth verification works with mocked settings."""
        mock_settings = create_mock_settings()
        
        with patch("src.webdeface.api.auth.get_settings", return_value=mock_settings):
            # Test valid token
            assert verify_api_token("test-token-123") is True
            
            # Test invalid token
            assert verify_api_token("invalid-token") is False

    def test_auth_verification_prevents_external_calls(self):
        """Test that auth verification doesn't make external calls."""
        mock_settings = create_mock_settings()
        
        # Track if any external calls are attempted
        external_call_attempted = False
        
        def track_external_call(*args, **kwargs):
            nonlocal external_call_attempted
            external_call_attempted = True
            return Mock()
        
        with patch("src.webdeface.api.auth.get_settings", return_value=mock_settings), \
             patch("requests.get", side_effect=track_external_call), \
             patch("aiohttp.ClientSession", side_effect=track_external_call):
            
            # Perform auth verification
            result = verify_api_token("test-token-123")
            
            # Should succeed without external calls
            assert result is True
            assert external_call_attempted is False

    @pytest.mark.asyncio
    async def test_claude_client_mocking_prevents_api_calls(self):
        """Test that Claude client mocking prevents real API calls."""
        from src.webdeface.classifier.claude import ClaudeClient
        
        mock_settings = create_mock_settings()
        api_call_attempted = False
        
        def track_api_call(*args, **kwargs):
            nonlocal api_call_attempted
            api_call_attempted = True
            raise RuntimeError("Real API call attempted!")
        
        with patch("src.webdeface.classifier.claude.get_settings", return_value=mock_settings), \
             patch("src.webdeface.classifier.claude.AsyncAnthropic", side_effect=track_api_call):
            
            try:
                client = ClaudeClient()
                # The constructor should not trigger actual API calls
                assert api_call_attempted is False
            except RuntimeError as e:
                if "Real API call attempted!" in str(e):
                    pytest.fail("Claude client constructor attempted real API call")

    def test_comprehensive_external_service_blocking(self):
        """Test that all external services are properly blocked."""
        mock_settings = create_mock_settings()
        blocked_services = []
        
        def track_blocked_service(service_name):
            def blocker(*args, **kwargs):
                blocked_services.append(service_name)
                return Mock()
            return blocker
        
        with patch("src.webdeface.config.settings.get_settings", return_value=mock_settings), \
             patch("aiohttp.ClientSession", side_effect=track_blocked_service("aiohttp")), \
             patch("requests.get", side_effect=track_blocked_service("requests")), \
             patch("anthropic.AsyncAnthropic", side_effect=track_blocked_service("anthropic")):
            
            # Test that basic config access works without external calls
            from src.webdeface.config.settings import get_settings
            settings = get_settings()
            
            # Should have mock settings without triggering external service calls
            assert settings.api_tokens == ["test-token-123"]
            assert len(blocked_services) == 0  # No external services should be called

    def test_token_verification_edge_cases(self):
        """Test edge cases in token verification."""
        mock_settings = create_mock_settings()
        
        with patch("src.webdeface.api.auth.get_settings", return_value=mock_settings):
            # Test empty token
            assert verify_api_token("") is False
            
            # Test None token
            assert verify_api_token(None) is False
            
            # Test whitespace token
            assert verify_api_token("   ") is False
            
            # Test correct token with extra whitespace
            assert verify_api_token("  test-token-123  ") is False  # Exact match required
            
            # Test partial token
            assert verify_api_token("test-token") is False