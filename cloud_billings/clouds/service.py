"""Cloud service base classes and provider factory.

This module provides base classes for cloud services and a factory
for creating cloud provider instances.
"""

import logging
from typing import Dict, Any, Optional

from .aws_provider import AWSConfig, AWSCloud
from .huawei_provider import HuaweiConfig, HuaweiCloud


# Configure logging
logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating cloud provider instances."""

    # Mapping of provider names to their config and provider classes
    PROVIDER_MAPPING = {
        'aws': {
            'config_class': AWSConfig,
            'provider_class': AWSCloud
        },
        'huawei': {
            'config_class': HuaweiConfig,
            'provider_class': HuaweiCloud
        }
    }

    @classmethod
    def create_provider(
        cls, provider_name: str, config: Optional[Dict[str, Any]] = {}
    ) -> Any:
        """Create a cloud provider instance.

        Args:
            provider_name (str): Name of the cloud provider
            config (Dict[str, Any]): Provider configuration

        Returns:
            Any: Cloud provider instance

        Raises:
            ValueError: If provider name is not supported
        """
        if provider_name not in cls.PROVIDER_MAPPING:
            raise ValueError(f"Unsupported provider: {provider_name}")

        provider_info = cls.PROVIDER_MAPPING[provider_name]
        config_class = provider_info['config_class']
        provider_class = provider_info['provider_class']

        # Create provider instance with validated config
        # Add fallback to empty dict if config is None
        config = config or {}
        logger.info(f"Creating provider instance with config: {config}")
        provider_config = config_class(**config)
        return provider_class(provider_config)


class BillingService:
    """Service for retrieving cloud billing information."""

    def __init__(self, provider_name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize billing service.

        Args:
            provider_name (str): Name of the cloud provider
            config (Dict[str, Any]): Provider configuration
        """
        self.provider = ProviderFactory.create_provider(
            provider_name, config
        )

    def get_billing_info(self, period: Optional[str] = None) -> Dict[str, Any]:
        """Get billing information.

        Args:
            period (Optional[str]): Period in YYYY-MM format. Defaults to
                current month if not specified.

        Returns:
            Dict[str, Any]: Billing information
        """
        return self.provider.get_billing_info(period=period)