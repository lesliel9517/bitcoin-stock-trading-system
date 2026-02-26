"""Configuration management"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager

    Supports loading configuration from YAML files and environment variables
    """

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager

        Args:
            config_dir: Configuration file directory, defaults to config folder in project root
        """
        # Load environment variables
        load_dotenv()

        # Set configuration directory
        if config_dir is None:
            # Default configuration directory
            project_root = Path(__file__).parent.parent.parent
            self.config_dir = project_root / "config"
        else:
            self.config_dir = Path(config_dir)

        self._configs: Dict[str, Any] = {}

    def load(self, config_name: str) -> Dict[str, Any]:
        """Load configuration file

        Args:
            config_name: Configuration file name (without .yaml extension)

        Returns:
            Configuration dictionary
        """
        if config_name in self._configs:
            return self._configs[config_name]

        config_path = self.config_dir / f"{config_name}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Replace environment variables
        config = self._replace_env_vars(config)

        self._configs[config_name] = config
        return config

    def _replace_env_vars(self, config: Any) -> Any:
        """Recursively replace environment variables in configuration

        Supports ${VAR_NAME} format environment variable references

        Args:
            config: Configuration object

        Returns:
            Configuration object with replaced values
        """
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Replace ${VAR_NAME} format environment variables
            if config.startswith("${") and config.endswith("}"):
                var_name = config[2:-1]
                return os.getenv(var_name, config)
            return config
        else:
            return config

    def get(self, config_name: str, key: str, default: Any = None) -> Any:
        """Get configuration value

        Args:
            config_name: Configuration file name
            key: Configuration key (supports dot-separated nested keys, e.g., "database.host")
            default: Default value

        Returns:
            Configuration value
        """
        config = self.load(config_name)

        # Support nested keys
        keys = key.split('.')
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def reload(self, config_name: Optional[str] = None):
        """Reload configuration

        Args:
            config_name: Configuration file name, if None reload all configurations
        """
        if config_name is None:
            self._configs.clear()
        else:
            self._configs.pop(config_name, None)


# Global configuration instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def load_config(config_name: str) -> Dict[str, Any]:
    """Load configuration file (convenience function)"""
    return get_config().load(config_name)
