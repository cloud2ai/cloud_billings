"""Cloud provider base module.

This module provides the base classes and interfaces for cloud providers.
It defines the common interface that all cloud providers must implement,
allowing for extensibility beyond just billing functionality.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class BaseCloudConfig:
    """Base configuration for cloud providers.

    Attributes:
        api_key (Optional[str]): API key for authentication
        api_secret (Optional[str]): API secret for authentication
        region (str): Cloud provider region
        timeout (int): Request timeout in seconds
        max_retries (int): Maximum number of retries for failed requests
    """
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    region: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3


class BaseCloudProvider(ABC):
    """Base class for cloud providers.

    This class defines the interface that all cloud providers must implement.
    It provides a common interface for different cloud providers like AWS,
    Azure, etc.

    The interface is designed to be extensible, allowing for various cloud
    operations beyond billing, such as resource management, monitoring, etc.
    """

    def __init__(self, config: BaseCloudConfig):
        """Initialize the cloud provider.

        Args:
            config (CloudConfig): Configuration for the provider
        """
        self.config = config

    @abstractmethod
    def get_billing_info(
        self, period: Optional[str] = None
    ) -> Tuple[float, str, Dict[str, float]]:
        """Get billing information for a specific period.

        Args:
            period (Optional[str]): Period in YYYY-MM format. Defaults to
                current month if not specified.

        Returns:
            Tuple[float, str, Dict[str, float]]: A tuple containing:
                - total_cost (float): Total cost for the period
                - currency (str): Currency of the cost
                - service_costs (Dict[str, float]): Cost breakdown by service

        Raises:
            Exception: If the billing information cannot be retrieved
        """
        raise NotImplementedError(
            "get_billing_info() method needs to be implemented"
        )

    @abstractmethod
    def get_account_id(self) -> str:
        """Get the cloud provider account ID.

        Returns:
            str: Cloud provider account ID

        Raises:
            Exception: If the account ID cannot be retrieved
        """
        raise NotImplementedError(
            "get_account_id() method needs to be implemented"
        )

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate the cloud provider credentials.

        Returns:
            bool: True if credentials are valid, False otherwise

        Raises:
            Exception: If the validation fails due to network or other issues
        """
        raise NotImplementedError(
            "validate_credentials() method needs to be implemented"
        )