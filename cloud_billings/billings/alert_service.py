"""Alert service for cloud billing system.

This module provides functionality to send alerts when billing costs
exceed certain thresholds.
"""

import logging
import requests
from datetime import datetime


# Configure logging
logger = logging.getLogger(__name__)


class AlertService:
    """Service for sending billing alerts."""

    def __init__(self, webhook_url: str):
        """Initialize alert service.

        Args:
            webhook_url (str): Webhook URL for sending alerts
        """
        self.webhook_url = webhook_url

    def send_alert(
        self,
        alert_message: str
    ) -> bool:
        """Send alert when cost increase exceeds threshold.

        Args:
            alert_message (str): Alert message

        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        try:
            # Calculate cost increase percentage
            # Prepare alert message
            message = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": "[重点关注]云平台账单消费提醒",
                            "content": [
                                [{
                                    "tag": "text",
                                    "text": alert_message
                                }, {
                                    "tag": "at",
                                    "user_id": "all"
                                }]
                            ]
                        }
                    }
                }
            }

            # Send webhook request
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            logger.info(f"response: {response.json()}")

            response.raise_for_status()

            logger.info(
                f"Alert sent successfully: {alert_message}"
            )
            return True

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to send alert: {str(e)}"
            )
            return False