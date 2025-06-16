"""Web Defacement Monitor - A sophisticated web monitoring and alerting system."""

__version__ = "0.1.0"
__author__ = "Daniel Bloom"

# Core exports
from .config import get_settings
from .main import main_api, main_cli

# Provide backwards compatibility
main = main_cli

__all__ = ["main_cli", "main_api", "main", "get_settings", "__version__"]
