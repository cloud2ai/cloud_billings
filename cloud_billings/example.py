"""Example usage of the cloud billing system.

This module demonstrates how to use the cloud billing system to retrieve
billing information from cloud providers.
"""

import logging
from datetime import datetime
import os

from cloud_billings.clouds.service import BillingService


# Configure logging
def setup_logging():
    """Configure logging for the application."""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # Configure example logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)


# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


def test_aws_billing():
    """Test AWS billing functionality."""
    # Create AWS billing service with configuration
    aws_config = {
        'api_key': os.getenv('AWS_ACCESS_KEY_ID'),
        'api_secret': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'region': os.getenv('AWS_REGION', 'cn-north-1')
    }

    billing_service = BillingService(
        provider_name='aws',
        config=aws_config
    )

    # Get billing information for specific period
    try:
        # Get current month's billing
        current_month = datetime.now().strftime("%Y-%m")
        result = billing_service.get_billing_info(period=current_month)

        if result["status"] == "success":
            data = result["data"]
            logger.info(f"\nAWS Billing for {current_month}:")
            logger.info(f"Total Cost: {data['total_cost']} {data['currency']}")
        else:
            logger.error(
                "Failed to get AWS billing information: %s",
                result['error']
            )

    except Exception as e:
        logger.error(f"An error occurred with AWS: {str(e)}")
        logger.exception(e)


def test_huawei_billing():
    """Test Huawei Cloud billing functionality."""
    # Create Huawei billing service with configuration
    huawei_config = {
        'api_key': os.getenv('ACCESS_KEY_ID'),
        'api_secret': os.getenv('SECRET_ACCESS_KEY'),
        'region': os.getenv('REGION', 'cn-north-1'),
        'is_international': (
            os.getenv('HUAWEI_IS_INTERNATIONAL', 'false').lower() == 'true'
        )
    }

    billing_service = BillingService(
        provider_name='huawei',
        config=huawei_config
    )

    # Get billing information for specific period
    try:
        # Get current month's billing
        current_month = datetime.now().strftime("%Y-%m")
        result = billing_service.get_billing_info(period=current_month)

        if result["status"] == "success":
            data = result["data"]
            logger.info(f"\nHuawei Cloud Billing for {current_month}:")
            logger.info(f"Total Cost: {data['total_cost']} {data['currency']}")
        else:
            logger.error(
                "Failed to get Huawei Cloud billing information: %s",
                result['error']
            )

    except Exception as e:
        logger.error(f"An error occurred with Huawei Cloud: {str(e)}")
        logger.exception(e)


def main():
    """Main function demonstrating billing system usage."""
    logger.info("Testing AWS billing...")
    test_aws_billing()

    logger.info("\nTesting Huawei Cloud billing...")
    test_huawei_billing()


if __name__ == "__main__":
    main()