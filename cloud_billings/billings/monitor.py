"""Cloud billing monitor.

This module monitors cloud billing costs and sends alerts when costs
exceed certain thresholds.
"""

import logging
import csv
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from cloud_billings.clouds.service import BillingService
from cloud_billings.billings.alert_service import AlertService
from cloud_billings.billings.config_parser import ConfigParser


# Configure logging
logger = logging.getLogger(__name__)


class BillingMonitor:
    """Monitor for cloud billing costs."""

    def __init__(
        self, 
        config_file: str, 
        data_dir: str, 
        webhook_url: str = None
    ):
        """Initialize billing monitor.

        Args:
            config_file (str): Path to configuration CSV file
            data_dir (str): Directory to store billing data
            webhook_url (str): Webhook URL for alerts
        """
        self.config_file = config_file
        self.data_dir = data_dir
        self.webhook_url = webhook_url
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Created data directory: {self.data_dir}")

    def _get_current_hour_file(self, provider_name: str) -> str:
        """Get filename for current hour.

        Args:
            provider_name (str): Name of the cloud provider

        Returns:
            str: Current hour's filename
        """
        timestamp = datetime.now().strftime("%Y-%m-%d-%H")
        return f"{provider_name}_{timestamp}.json"

    def _get_billing_data(
        self, 
        provider_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get billing data from current hour's file if exists.

        Args:
            provider_name (str): Name of the cloud provider

        Returns:
            Optional[Dict[str, Any]]: Billing data if exists
        """
        current_file = self._get_current_hour_file(provider_name)
        file_path = os.path.join(self.data_dir, current_file)
        
        if os.path.exists(file_path):
            msg = f"Using cached data for {provider_name} from {current_file}"
            logger.info(msg)
            with open(file_path, 'r') as f:
                return json.load(f)
        return None

    def _save_billing_data(
        self, 
        provider_name: str, 
        data: Dict[str, Any]
    ):
        """Save billing data to file.

        Args:
            provider_name (str): Name of the cloud provider
            data (Dict[str, Any]): Billing data to save
        """
        filename = self._get_current_hour_file(provider_name)
        filepath = os.path.join(self.data_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved billing data to {filepath}")

    def _get_previous_billing(
        self, 
        provider_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get previous billing data for a provider.

        Args:
            provider_name (str): Name of the cloud provider

        Returns:
            Optional[Dict[str, Any]]: Previous billing data if exists
        """
        files = [
            f for f in os.listdir(self.data_dir)
            if f.startswith(provider_name) and f.endswith('.json')
        ]
        if not files:
            return None

        # 获取当前小时的文件名
        current_file = self._get_current_hour_file(provider_name)
        # 排除当前小时的文件
        files = [f for f in files if f != current_file]
        if not files:
            return None

        latest_file = max(files)
        with open(os.path.join(self.data_dir, latest_file), 'r') as f:
            return json.load(f)

    def _fetch_and_save_billing(
        self, 
        provider: Dict[str, str]
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Fetch and save billing data for a provider.

        Args:
            provider (Dict[str, str]): Provider configuration

        Returns:
            Tuple[str, Optional[Dict[str, Any]]]: Provider name and current 
            billing data
        """
        provider_name = provider['name']
        logger.info(f"Processing provider: {provider_name}")

        # 检查当前小时是否已有数据
        cached_data = self._get_billing_data(provider_name)
        if cached_data:
            logger.info(f"Using current hour's data for {provider_name}")
            return provider_name, cached_data

        try:
            # 如果没有当前小时的数据，获取新数据
            config_dict = ConfigParser.parse(provider['config'])
            msg = f"No current hour data found, fetching new data for {provider_name}"
            logger.info(msg)

            # Load environment variables from config
            for key, value in config_dict.items():
                if value:  # Only set non-empty values
                    os.environ[key] = str(value)
                    logger.info("Set environment variable: %s=***", key)

            # Create billing service and get current billing
            billing_service = BillingService(
                provider_name=provider['provider']
            )
            current_month = datetime.now().strftime("%Y-%m")
            billing_info = billing_service.get_billing_info(
                period=current_month
            )
            result = billing_info

            if result['status'] != 'success':
                logger.error(
                    "Failed to get billing for %s: %s",
                    provider_name,
                    result['error']
                )
                return provider_name, None

            current_data = result['data']
            self._save_billing_data(provider_name, current_data)
            return provider_name, current_data

        except Exception as e:
            msg = f"Error processing provider {provider_name}: {str(e)}"
            logger.error(msg)
            logger.exception(e)
            return provider_name, None

    def _compare_billing_data(
        self,
        provider_name: str,
        current_data: Optional[Dict[str, Any]],
        threshold: float = 5
    ) -> Optional[Dict[str, Any]]:
        """Compare current billing with previous billing.

        Args:
            provider_name (str): Name of the cloud provider
            current_data (Optional[Dict[str, Any]]): Current billing data
            threshold (float): Alert threshold percentage

        Returns:
            Optional[Dict[str, Any]]: Alert data if threshold exceeded
        """
        if not current_data:
            return None

        previous_data = self._get_previous_billing(provider_name)
        if not previous_data:
            return None

        current_cost = current_data['total_cost']
        previous_cost = previous_data['total_cost']
        msg = f"current_cost: {current_cost}, previous_cost: {previous_cost}"
        logger.info(msg)
        
        if previous_cost > 0:
            increase_percent = (
                (current_cost - previous_cost) / previous_cost
            ) * 100
            msg = f"increase_percent: {increase_percent} {threshold}"
            logger.info(msg)
            
            if increase_percent > threshold:
                return {
                    'provider_name': provider_name,
                    'current_cost': current_cost,
                    'previous_cost': previous_cost,
                    'increase_percent': increase_percent,
                    'currency': current_data['currency']
                }
        
        return None

    def _send_alerts(self, alert_message: str):
        """Send alerts if billing exceeds threshold.

        Args:
            alert_data (Dict[str, Any]): Alert data
        """
        try:
            alert_service = AlertService(self.webhook_url)
            alert_service.send_alert(alert_message=alert_message)
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")
            logger.exception(e)

    def run(self):
        """Run billing monitor."""
        try:
            # Read configuration
            with open(self.config_file, 'r') as f:
                reader = csv.DictReader(f)
                providers = list(reader)

            alerts = []
            # Process each provider
            for provider in providers:
                display_name = provider['display_name']
                # Step 1: Fetch and save billing data
                provider_name, current_data = self._fetch_and_save_billing(
                    provider
                )
                
                # Step 2: Compare with previous billing
                alert_data = self._compare_billing_data(
                    provider_name, 
                    current_data
                )
                if alert_data:
                    alert_data['display_name'] = display_name
                    alerts.append(alert_data)

            if self.webhook_url:
                logger.info(f"alerts: {alerts}")
                alert_messages = []
                for alert in alerts:
                    increse_cost = round(
                        alert['current_cost'] - alert['previous_cost'], 
                        2
                    )
                    currency = alert['currency']
                    msg = (
                        f"{alert['display_name']} 账户在过去一小时的消费增长了 "
                        f"{increse_cost} {currency}\n"
                    )
                    alert_messages.append(msg)

                if alert_messages:
                    alert_message = "\n".join(alert_messages)
                    logger.info(f"alert_message: {alert_message}")
                    self._send_alerts(alert_message)

        except Exception as e:
            logger.error(f"Error reading configuration: {str(e)}")
            raise