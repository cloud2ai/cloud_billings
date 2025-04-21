from typing import Dict


class ConfigParser:
    """
    Parser for configuration strings in format: key1=value1|key2=value2
    """
    @staticmethod
    def parse(config_str: str) -> Dict[str, str]:
        """
        Parse configuration string into dictionary.

        Args:
            config_str: Configuration string in format key1=value1|key2=value2

        Returns:
            Dictionary containing parsed configuration
        """
        if not config_str:
            return {}

        config = {}
        items = config_str.split('|')
        for item in items:
            if '=' not in item:
                continue
            key, value = item.split('=', 1)
            config[key.strip()] = value.strip()

        return config

    @staticmethod
    def format(config: Dict[str, str]) -> str:
        """
        Format dictionary into configuration string.

        Args:
            config: Dictionary containing configuration

        Returns:
            Configuration string in format key1=value1|key2=value2
        """
        return '|'.join(f"{k}={v}" for k, v in config.items())