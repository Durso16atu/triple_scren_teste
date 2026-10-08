import re

with open('src/monitor_realtime.py', 'r') as f:
    content = f.read()

content = content.replace("            except Exception as e:\n                continue", "            except Exception as e:\n                import traceback; traceback.print_exc()\n                continue")

with open('src/monitor_realtime.py', 'w') as f:
    f.write(content)
