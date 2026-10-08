import re

with open('src/monitor_realtime.py', 'r') as f:
    content = f.read()

content = content.replace("grades_ativas = {}", "grades_ativas = {}\n        precos_spot = {}")
content = content.replace(
    "grades_ativas[ticker] = df_g.to_dict(orient=\"records\")",
    "grades_ativas[ticker] = df_g.to_dict(orient=\"records\")\n                precos_spot[ticker] = spot_ticker"
)
content = content.replace(
    "\"grades_por_ativo\": grades_ativas",
    "\"grades_por_ativo\": grades_ativas,\n            \"precos_spot\": precos_spot"
)

with open('src/monitor_realtime.py', 'w') as f:
    f.write(content)
