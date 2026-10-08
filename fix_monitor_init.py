with open('src/monitor_realtime.py', 'r') as f:
    content = f.read()

content = content.replace(
    "self.webhook = webhook or WebhookDispatcher()",
    "self.webhook = webhook or WebhookDispatcher()\n        self.validator = OptionsMarketValidator(timeout_sec=3)"
)

# And let's remove the exception tracebacks I added earlier:
content = content.replace("            except Exception as e:\n                import traceback; traceback.print_exc()\n                continue", "            except Exception as e:\n                continue")

with open('src/monitor_realtime.py', 'w') as f:
    f.write(content)
