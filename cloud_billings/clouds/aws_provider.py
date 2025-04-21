"""AWS cloud provider implementation.

This module provides an implementation of the Cloud interface for AWS.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

from .provider import BaseCloudProvider, BaseCloudConfig


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AWSConfig(BaseCloudConfig):
    """AWS cloud provider configuration.

    This configuration class extends the base CloudConfig and adds AWS-specific
    configuration options. If values are not provided, they will be read from
    environment variables.

    Environment Variables:
        AWS_ACCESS_KEY_ID: AWS access key
        AWS_SECRET_ACCESS_KEY: AWS secret key
        AWS_REGION: AWS region
        AWS_TIMEOUT: Request timeout in seconds
        AWS_MAX_RETRIES: Maximum number of retries for failed requests
    """
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    region: str = "cn-north-1"  # Default region
    timeout: int = 30
    max_retries: int = 3

    def __post_init__(self):
        """Initialize configuration from environment variables if not set."""
        if self.api_key is None:
            self.api_key = os.getenv("AWS_ACCESS_KEY_ID")
        if self.api_secret is None:
            self.api_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        if self.region is None:
            self.region = os.getenv("AWS_REGION", "cn-north-1")
        if self.timeout == 30:
            self.timeout = int(os.getenv("AWS_TIMEOUT", "30"))
        if self.max_retries == 3:
            self.max_retries = int(os.getenv("AWS_MAX_RETRIES", "3"))

        self._validate_config()

    def _validate_config(self):
        """Validate configuration parameters.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not self.api_key:
            raise ValueError(
                "AWS access key is required. Set it via constructor or "
                "AWS_ACCESS_KEY_ID environment variable."
            )

        if not self.api_secret:
            raise ValueError(
                "AWS secret key is required. Set it via constructor or "
                "AWS_SECRET_ACCESS_KEY environment variable."
            )

        if not self.region:
            raise ValueError(
                "AWS region is required. Set it via constructor or "
                "AWS_REGION environment variable."
            )

        if self.timeout <= 0:
            raise ValueError("Timeout must be greater than 0")

        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")


class AWSCloud(BaseCloudProvider):
    """AWS cloud provider implementation."""

    def __init__(self, config: AWSConfig):
        """Initialize AWS cloud provider.

        Args:
            config (AWSConfig): AWS configuration

        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(config)
        self._client = None
        self._sts_client = None
        self.name = "aws"
        logger.info(f"Initialized AWS Cloud provider with config: {config}")

    @property
    def client(self):
        """Get AWS Cost Explorer client."""
        if self._client is None:
            self._client = boto3.client(
                'ce',
                aws_access_key_id=self.config.api_key,
                aws_secret_access_key=self.config.api_secret,
                region_name=self.config.region
            )
        return self._client

    @property
    def sts_client(self):
        """Get AWS STS client."""
        if self._sts_client is None:
            self._sts_client = boto3.client(
                'sts',
                aws_access_key_id=self.config.api_key,
                aws_secret_access_key=self.config.api_secret,
                region_name=self.config.region
            )
        return self._sts_client

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

    def _get_period_dates(self, period: str) -> Tuple[str, str]:
        """Get start and end dates for the billing period.

        Args:
            period (str): Period in YYYY-MM format

        Returns:
            Tuple[str, str]: Start and end dates in YYYY-MM-DD format
        """
        year, month = map(int, period.split("-"))
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        last_day = (
            datetime(next_year, next_month, 1) - timedelta(days=1)
        ).day

        return f"{period}-01", f"{period}-{last_day:02d}"

    def _query_billing_api(
        self, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Query the AWS Cost Explorer API.

        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format

        Returns:
            Dict[str, Any]: API response containing cost and usage data
        """
        logger.debug(
            f"Using AWS configuration: region={self.config.region}, "
            f"access_key={self.config.api_key[:4]}***"
        )

        response = self.client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost']
        )

        logger.debug(f"Received response: {response}")
        return response

    def _calculate_total_cost(
        self, response: Dict[str, Any]
    ) -> Tuple[float, str]:
        """Calculate total cost from billing API response.

        Args:
            response (Dict[str, Any]): API response object

        Returns:
            Tuple[float, str]: Total cost and currency
        """
        result = response['ResultsByTime'][0]['Total']['UnblendedCost']
        total_cost = float(result['Amount'])
        currency = result['Unit']

        logger.debug(
            f"Calculated total cost: {total_cost} {currency}"
        )

        return total_cost, currency

    def get_billing_info(
        self, period: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get AWS billing information for a specific period.

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
                        "account_id": str
                    } | None,
                    "error": str | None
                }
        """
        try:
            # Validate and get billing period
            period = self._validate_period(period)

            # Get period dates
            start_date, end_date = self._get_period_dates(period)

            # Query billing API
            response = self._query_billing_api(start_date, end_date)

            # Calculate total cost
            total_cost, currency = self._calculate_total_cost(response)

            # Get account ID
            account_id = self.get_account_id()

            # Build response data
            data = {
                "total_cost": total_cost,
                "currency": currency,
                "account_id": account_id
            }

            logger.info(f"AWS billing data: {data}")

            return {
                "status": "success",
                "data": data,
                "error": None
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(
                f"AWS API Error: {error_code} - {error_message}\n"
                f"Region: {self.config.region}\n"
                f"Access Key: {self.config.api_key[:4]}***"
            )

            if error_code == 'UnrecognizedClientException':
                logger.error(
                    "Possible causes:\n"
                    "1. Invalid or expired AWS credentials\n"
                    "2. Mismatch between credentials and region "
                    "(global vs China)\n"
                    "3. Missing required permissions for Cost Explorer API"
                )
            return {
                "status": "error",
                "data": None,
                "error": f"AWS API Error: {error_code} - {error_message}"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            logger.exception(e)
            return {
                "status": "error",
                "data": None,
                "error": str(e)
            }

    def get_account_id(self) -> str:
        """Get AWS account ID.

        Returns:
            str: AWS account ID

        Raises:
            Exception: If the account ID cannot be retrieved
        """
        try:
            response = self.sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            logger.error(f"Failed to get AWS account ID: {str(e)}")
            logger.exception(e)
            raise

    def validate_credentials(self) -> bool:
        """Validate AWS credentials.

        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            self.sts_client.get_caller_identity()
            return True
        except Exception as e:
            logger.error(f"Failed to validate AWS credentials: {str(e)}")
            logger.exception(e)
            return False