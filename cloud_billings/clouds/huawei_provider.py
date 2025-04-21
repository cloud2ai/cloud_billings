"""Huawei cloud provider implementation.

This module provides an implementation of the Cloud interface for Huawei Cloud.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbssintl.v2 import BssintlClient
from huaweicloudsdkbssintl.v2.region.bssintl_region import BssintlRegion
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.region.bss_region import BssRegion
from huaweicloudsdkbssintl.v2.model import (
    ListMonthlyExpendituresRequest
)
from huaweicloudsdkbss.v2.model import (
    ShowCustomerMonthlySumRequest
)
from huaweicloudsdkcore.exceptions import exceptions

from .provider import BaseCloudProvider, BaseCloudConfig


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class HuaweiConfig(BaseCloudConfig):
    """Huawei cloud provider configuration.

    This configuration class extends the base CloudConfig and adds
    Huawei-specific configuration options. If values are not provided,
    they will be read from environment variables.

    Environment Variables:
        HUAWEI_ACCESS_KEY_ID: Huawei access key
        HUAWEI_SECRET_ACCESS_KEY: Huawei secret key
        HUAWEI_REGION: Huawei region
        HUAWEI_PROJECT_ID: Huawei project ID (optional)
        HUAWEI_IS_INTERNATIONAL: Whether to use international site (default: false)
    """
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    region: Optional[str] = None  # Default Singapore region
    project_id: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    is_international: bool = False

    def __post_init__(self):
        """Initialize configuration from environment variables if not set."""
        if self.api_key is None:
            self.api_key = os.getenv("HUAWEI_ACCESS_KEY_ID")
        if self.api_secret is None:
            self.api_secret = os.getenv("HUAWEI_SECRET_ACCESS_KEY")
        if self.region is None:
            self.region = os.getenv("HUAWEI_REGION", "cn-north-1")
        if self.project_id is None:
            self.project_id = os.getenv("HUAWEI_PROJECT_ID")
        if self.timeout == 30:
            self.timeout = int(os.getenv("HUAWEI_TIMEOUT", "30"))
        if self.max_retries == 3:
            self.max_retries = int(os.getenv("HUAWEI_MAX_RETRIES", "3"))
        if not self.is_international:
            self.is_international = os.getenv(
                "HUAWEI_IS_INTERNATIONAL", "false"
            ).lower() == "true"

        self._validate_config()

    def _validate_config(self):
        """Validate configuration parameters.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not self.api_key:
            raise ValueError(
                "Huawei access key is required. Set it via constructor or "
                "HUAWEI_ACCESS_KEY_ID environment variable."
            )

        if not self.api_secret:
            raise ValueError(
                "Huawei secret key is required. Set it via constructor or "
                "HUAWEI_SECRET_ACCESS_KEY environment variable."
            )

        if not self.region:
            raise ValueError(
                "Huawei region is required. Set it via constructor or "
                "HUAWEI_REGION environment variable."
            )

        if self.timeout <= 0:
            raise ValueError("Timeout must be greater than 0")

        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")


class HuaweiCloud(BaseCloudProvider):
    """Huawei cloud provider implementation."""

    def __init__(self, config: HuaweiConfig):
        """Initialize Huawei cloud provider.

        Args:
            config (HuaweiConfig): Huawei configuration

        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(config)
        self._client = None
        self.name = "huawei"
        logger.info(f"Initialized Huawei Cloud provider with config: {config}")

    @property
    def client(self):
        """Get Huawei BSS client."""
        if self._client is None:
            logger.debug("Creating new Huawei BSS client")
            credentials = GlobalCredentials(
                self.config.api_key,
                self.config.api_secret
            )
            if self.config.is_international:
                self._client = BssintlClient.new_builder() \
                    .with_credentials(credentials) \
                    .with_region(BssintlRegion.value_of(self.config.region)) \
                    .build()
            else:
                self._client = BssClient.new_builder() \
                    .with_credentials(credentials) \
                    .with_region(BssRegion.value_of(self.config.region)) \
                    .build()
        return self._client

    def _convert_amount(self, amount: float, measure_id: int) -> float:
        """Convert amount based on measure_id.

        Args:
            amount (float): Original amount
            measure_id (int): Amount unit (1: yuan, 3: fen)

        Returns:
            float: Converted amount in yuan
        """
        if measure_id == 3:  # fen to yuan
            return amount / 100
        return amount

    def _validate_period(self, period: Optional[str]) -> str:
        """Validate and return the billing period.

        Args:
            period (Optional[str]): Period in YYYY-MM format

        Returns:
            str: Validated period

        Raises:
            ValueError: If period format is invalid
        """
        if period is None:
            period = datetime.now().strftime("%Y-%m")

        logger.info(f"Getting billing info for period: {period}")

        try:
            year, month = map(int, period.split("-"))
            if not (1 <= month <= 12):
                raise ValueError("Month must be between 1 and 12")
        except ValueError as e:
            raise ValueError(f"Invalid period format: {str(e)}")

        return period

    def _query_billing_api(self, period: str) -> Any:
        """Query the Huawei billing API.

        Args:
            period (str): Period in YYYY-MM format

        Returns:
            Any: API response object

        Raises:
            exceptions.ClientRequestException: If API request fails
        """
        logger.debug(
            f"Using Huawei configuration: region={self.config.region}, "
            f"project_id={self.config.project_id}"
        )

        if self.config.is_international:
            request = ListMonthlyExpendituresRequest()
            request.cycle = period
        else:
            request = ShowCustomerMonthlySumRequest()
            request.bill_cycle = period

        logger.debug(f"Prepared request: {request}")
        logger.info("Sending request to Huawei BSS API")

        if self.config.is_international:
            response = self.client.list_monthly_expenditures(request)
        else:
            response = self.client.show_customer_monthly_sum(request)

        logger.debug(f"Received response: {response}")

        if not hasattr(response, 'bill_sums'):
            raise ValueError("Invalid response format: missing bill_sums")

        return response

    def _calculate_total_cost(
        self, response: Any
    ) -> Tuple[float, str, List[Dict]]:
        """Calculate total cost from billing API response.

        Args:
            response (Any): API response object

        Returns:
            Tuple[float, str, List[Dict]]: Total cost, currency, and item details
        """
        currency = getattr(response, 'currency', 'USD')
        logger.debug(f"Currency from response: {currency}")

        total_cost = 0.0
        item_details = []

        for bill in response.bill_sums:
            measure_id = getattr(bill, 'measure_id', 3)
            amount = self._convert_amount(
                float(bill.consume_amount), measure_id
            )
            total_cost += amount

            service_type_name = getattr(
                bill, 'service_type_name', 'Unknown'
            )
            resource_type_name = getattr(
                bill, 'resource_type_name', 'Unknown'
            )
            service_name = f"{service_type_name} - {resource_type_name}"

            item_details.append({
                "service_name": service_name,
                "amount": amount,
                "measure_id": measure_id
            })

            logger.debug(
                f"Processed bill: service={service_name}, "
                f"amount={amount}, measure_id={measure_id}"
            )

        return total_cost, currency, item_details

    def get_billing_info(
        self, period: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get Huawei billing information for a specific period.

        Args:
            period (Optional[str]): Period in YYYY-MM format. Defaults to
                current month if not specified.

        Returns:
            Dict[str, Any]: Dictionary containing billing information
                in the following format:
                {
                    "status": "success" | "error",
                    "data": {
                        "total_cost": float,
                        "currency": str,
                        "account_id": str,
                        "items": List[Dict]
                    } | None,
                    "error": str | None
                }
        """
        try:
            # Validate and get billing period
            period = self._validate_period(period)

            # Query billing API
            response = self._query_billing_api(period)

            # Calculate total cost and get item details
            total_cost, currency, item_details = self._calculate_total_cost(
                response
            )

            # Build response data
            data = {
                "total_cost": total_cost,
                "currency": currency,
                "account_id": self.config.project_id or "default",
                "items": item_details
            }

            logger.info(f"Huawei billing data: {data}")

            return {
                "status": "success",
                "data": data,
                "error": None
            }

        except exceptions.ClientRequestException as e:
            error_msg = (
                f"Huawei API Error: {e.error_code} - {e.error_msg}\n"
                f"Status Code: {e.status_code}\n"
                f"Request ID: {e.request_id}"
            )
            logger.error(error_msg)
            return {
                "status": "error",
                "data": None,
                "error": error_msg
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Huawei API Error: {error_msg}")
            return {
                "status": "error",
                "data": None,
                "error": error_msg
            }

    def get_account_id(self) -> str:
        """Get Huawei project ID.

        Returns:
            str: Huawei project ID or 'default' if not set
        """
        return self.config.project_id or "default"

    def validate_credentials(self) -> bool:
        """Validate Huawei credentials.

        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            # Try to get billing info for current month
            result = self.get_billing_info()
            return result["status"] == "success"
        except Exception as e:
            logger.error(f"Failed to validate Huawei credentials: {str(e)}")
            return False