"""Cloud billing monitor entry point.

This script runs the cloud billing monitor to check costs and send alerts.
"""

import logging
import argparse
import os
from cloud_billings.billings.monitor import BillingMonitor


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


def parse_args():
    """Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Cloud billing monitor to check costs and send alerts'
    )
    parser.add_argument(
        '--config',
        required=True,
        help='Path to the configuration CSV file'
    )
    parser.add_argument(
        '--data-dir',
        required=True,
        help='Path to the data directory'
    )
    parser.add_argument(
        '--webhook-url',
        required=False,
        help='Webhook URL for alerts'
    )
    return parser.parse_args()


def ensure_data_dir(data_dir: str):
    """Ensure data directory exists.

    Args:
        data_dir (str): Path to the data directory
    """
    if not os.path.exists(data_dir):
        logger = logging.getLogger(__name__)
        logger.info(f"Creating data directory: {data_dir}")
        os.makedirs(data_dir, exist_ok=True)


def main():
    """Run the billing monitor."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Parse command line arguments
        args = parse_args()

        # Ensure data directory exists
        ensure_data_dir(args.data_dir)

        # Create and run monitor
        monitor = BillingMonitor(args.config, args.data_dir, args.webhook_url)
        monitor.run()

    except Exception as e:
        logger.error(f"Error running monitor: {str(e)}")
        raise


if __name__ == "__main__":
    main()