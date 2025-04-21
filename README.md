## Project Background

In our daily development work, we frequently use multi-cloud environments for testing and deployment. Since our product is built on a cloud-native architecture, we often need to dynamically create and destroy pay-as-you-go resources such as compute instances, storage volumes, and networking components. However, during this process, it's common to overlook and forget to delete some temporary resources, leading to idle resources that continue to incur costs—resulting in unnecessary cloud spending.

Currently, there is a lack of monitoring tools that are truly suitable for multi-cloud environments, easy to operate, and comprehensive in coverage. As a result, we decided to develop a lightweight tool to monitor abnormal resource consumption across cloud platforms.

Given the complexity and variety of cloud resources, integrating with each type of resource would be time-consuming and costly. Therefore, we chose to start from billing data. By monitoring hourly changes in cloud platform billing, we can quickly detect unusual spending patterns and trace them back to potential resource waste. This approach is highly generalizable, easy to adapt to different cloud vendors, and offers an efficient way to improve cost control in daily development and operations.  

Currently, alerts can be sent directly to Feishu via Webhook for timely team notifications.

## Installation

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Or install only core dependencies
pip install -e .
```

## Configuration

1. Create a configuration file (e.g., `config.csv`) with the following format:

```csv
name,provider,config,display_name,webhook_url
aws_china,aws,region=cn-north-1|api_key=YOUR_KEY|api_secret=YOUR_SECRET,AWS China,https://open.feishu.cn/open-apis/bot/v2/hook/xxx
huawei_china,huawei,region=cn-north-1|api_key=YOUR_KEY|api_secret=YOUR_SECRET,Huawei Cloud,https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

Configuration fields:
- `name`: Unique identifier for the provider
- `provider`: Cloud provider type (aws, huawei)
- `config`: Provider-specific configuration in key=value format
- `display_name`: Display name for alerts
- `webhook_url`: Feishu webhook URL for alerts (optional)

## Usage

### Command Line Interface

```bash
# Basic usage
cloud-billing-monitor --config /path/to/config.csv --data-dir /path/to/data

# Help message
cloud-billing-monitor --help
```

### Python Module

```python
from cloud_billings.billings.monitor import BillingMonitor

# Initialize monitor
monitor = BillingMonitor(
    config_file="/path/to/config.csv",
    data_dir="/path/to/data",
    webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"  # optional
)

# Run monitor
monitor.run()
```

## Features

- **Multi-Cloud Support**: Monitor billing across different cloud providers
- **Real-time Monitoring**: Check billing changes hourly
- **Cost Anomaly Detection**: Alert on unusual spending patterns
- **Feishu Integration**: Send alerts directly to Feishu
- **Data Persistence**: Store billing history for trend analysis
- **Easy Configuration**: Simple CSV-based configuration

## Data Storage

Billing data is stored in JSON format with hourly granularity:
```
data/
  ├── aws_china_2024-04-21-10.json
  ├── aws_china_2024-04-21-11.json
  ├── huawei_china_2024-04-21-10.json
  └── huawei_china_2024-04-21-11.json
```

## Alert Threshold

By default, the system alerts when the cost increase exceeds 5% compared to the previous hour. This threshold can be adjusted in the code.
