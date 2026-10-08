import re

with open('src/monitor_realtime.py', 'r') as f:
    content = f.read()

content = content.replace(
    "    from src.webhook_dispatcher import WebhookDispatcher\nfrom src.options_market_validator import OptionsMarketValidator",
    "    from src.webhook_dispatcher import WebhookDispatcher\n    from src.options_market_validator import OptionsMarketValidator"
)

with open('src/monitor_realtime.py', 'w') as f:
    f.write(content)
