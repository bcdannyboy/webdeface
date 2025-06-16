"""Configuration loading and persistence utilities."""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from .types import ConfigError, ConfigLoadError, GlobalConfiguration, SiteConfiguration

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Handles loading and saving configuration from multiple sources."""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config.yaml")
        self._cache: Optional[dict[str, Any]] = None

    def load_yaml_config(self) -> dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_file.exists():
            logger.warning(f"Config file {self.config_file} not found, using defaults")
            return {}

        try:
            with open(self.config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            logger.info(f"Loaded configuration from {self.config_file}")
            self._cache = config
            return config

        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Failed to parse YAML config: {str(e)}") from e
        except Exception as e:
            raise ConfigLoadError(f"Failed to load config file: {str(e)}") from e

    def save_yaml_config(self, config: dict[str, Any]) -> None:
        """Save configuration to YAML file."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)

            logger.info(f"Saved configuration to {self.config_file}")
            self._cache = config

        except Exception as e:
            raise ConfigError(f"Failed to save config file: {str(e)}") from e

    def get_global_config(self) -> GlobalConfiguration:
        """Get global configuration."""
        config = self.load_yaml_config()
        global_data = config.get("global", {})
        return GlobalConfiguration.from_dict(global_data)

    def get_sites_config(self) -> list[SiteConfiguration]:
        """Get sites configuration."""
        config = self.load_yaml_config()
        sites_data = config.get("sites", [])

        sites = []
        for site_data in sites_data:
            try:
                site = SiteConfiguration.from_dict(site_data)
                sites.append(site)
            except Exception as e:
                logger.error(
                    f"Failed to parse site config: {site_data}, error: {str(e)}"
                )

        return sites

    def add_site(self, site: SiteConfiguration) -> None:
        """Add a new site to configuration."""
        config = self.load_yaml_config()

        if "sites" not in config:
            config["sites"] = []

        # Check if site already exists
        for existing_site in config["sites"]:
            if existing_site.get("url") == site.url:
                raise ConfigError(f"Site {site.url} already exists in configuration")

        # Add new site
        config["sites"].append(site.to_dict())
        self.save_yaml_config(config)

    def remove_site(self, url: str) -> bool:
        """Remove a site from configuration."""
        config = self.load_yaml_config()

        if "sites" not in config:
            return False

        original_count = len(config["sites"])
        config["sites"] = [s for s in config["sites"] if s.get("url") != url]

        if len(config["sites"]) < original_count:
            self.save_yaml_config(config)
            return True

        return False

    def update_site(self, site: SiteConfiguration) -> bool:
        """Update an existing site configuration."""
        config = self.load_yaml_config()

        if "sites" not in config:
            return False

        for i, existing_site in enumerate(config["sites"]):
            if existing_site.get("url") == site.url:
                config["sites"][i] = site.to_dict()
                self.save_yaml_config(config)
                return True

        return False

    def update_global_config(self, global_config: GlobalConfiguration) -> None:
        """Update global configuration."""
        config = self.load_yaml_config()

        # Convert GlobalConfiguration to dict
        global_dict = {
            "default_interval": global_config.default_interval,
            "keep_scans": global_config.keep_scans,
            "alert": {
                "site_down": {
                    "channels": global_config.alert.site_down.channels,
                    "users": global_config.alert.site_down.users,
                },
                "benign_change": {
                    "channels": global_config.alert.benign_change.channels,
                    "users": global_config.alert.benign_change.users,
                },
                "defacement": {
                    "channels": global_config.alert.defacement.channels,
                    "users": global_config.alert.defacement.users,
                },
            },
        }

        config["global"] = global_dict
        self.save_yaml_config(config)

    def backup_config(self, backup_path: Optional[Path] = None) -> Path:
        """Create a backup of the current configuration."""
        if backup_path is None:
            backup_path = self.config_file.with_suffix(
                f".backup.{self.config_file.suffix}"
            )

        if self.config_file.exists():
            import shutil

            shutil.copy2(self.config_file, backup_path)
            logger.info(f"Configuration backed up to {backup_path}")

        return backup_path

    def restore_config(self, backup_path: Path) -> None:
        """Restore configuration from backup."""
        if not backup_path.exists():
            raise ConfigError(f"Backup file {backup_path} does not exist")

        import shutil

        shutil.copy2(backup_path, self.config_file)
        self._cache = None  # Clear cache
        logger.info(f"Configuration restored from {backup_path}")

    def validate_config(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        try:
            config = self.load_yaml_config()
        except Exception as e:
            return [f"Failed to load config: {str(e)}"]

        # Validate global section
        if "global" in config:
            global_config = config["global"]

            # Check required fields
            if "default_interval" not in global_config:
                issues.append("Missing global.default_interval")

            if "alert" in global_config:
                alert_config = global_config["alert"]
                for alert_type in ["site_down", "benign_change", "defacement"]:
                    if alert_type in alert_config:
                        alert_targets = alert_config[alert_type]
                        if not isinstance(alert_targets, (list, dict)):
                            issues.append(
                                f"Invalid format for global.alert.{alert_type}"
                            )

        # Validate sites section
        if "sites" in config:
            for i, site in enumerate(config["sites"]):
                if not isinstance(site, dict):
                    issues.append(f"Site {i} is not a valid object")
                    continue

                if "url" not in site:
                    issues.append(f"Site {i} missing required 'url' field")

                if "interval" in site:
                    # Basic cron validation (could be more thorough)
                    interval = site["interval"]
                    if not isinstance(interval, str) or len(interval.split()) != 5:
                        issues.append(
                            f"Site {i} has invalid interval format: {interval}"
                        )

        return issues


def create_example_config(config_path: Path) -> None:
    """Create an example configuration file."""
    example_config = {
        "global": {
            "default_interval": "*/15 * * * *",
            "keep_scans": 20,
            "alert": {
                "site_down": {"channels": ["#noc"], "users": []},
                "benign_change": {"channels": [], "users": []},
                "defacement": {"channels": ["#sec-ops"], "users": ["@security-team"]},
            },
        },
        "sites": [
            {
                "url": "https://example.com",
                "name": "Example Site",
                "interval": "0,30 * * * *",
                "depth": 2,
                "enabled": True,
            }
        ],
    }

    loader = ConfigLoader(config_path)
    loader.save_yaml_config(example_config)
