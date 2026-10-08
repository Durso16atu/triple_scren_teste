import re

with open('src/monitor_realtime.py', 'r') as f:
    content = f.read()

content = content.replace(
    "grade_opcoes_ciclo = oportunidades[0].grade_opcoes",
    "grade_opcoes_ciclo = grades_ativas.get(oportunidades[0].ticker_ativo, oportunidades[0].grade_opcoes)"
)

with open('src/monitor_realtime.py', 'w') as f:
    f.write(content)
