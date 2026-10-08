import re

with open('src/monitor_realtime.py', 'r') as f:
    content = f.read()

# Add holidays check
holidays_list = """FERIADOS_B3_2026 = [
    '2026-01-01', '2026-02-16', '2026-02-17', '2026-04-03', '2026-04-21',
    '2026-05-01', '2026-06-04', '2026-09-07', '2026-10-12', '2026-11-02',
    '2026-11-15', '2026-11-20', '2026-12-25'
]"""

if "FERIADOS_B3_2026 =" not in content:
    content = content.replace('TZ_SP = ZoneInfo("America/Sao_Paulo")', 'TZ_SP = ZoneInfo("America/Sao_Paulo")\n' + holidays_list)

content = content.replace(
    'eh_dia_util = agora_sp.weekday() < 5',
    'eh_dia_util = (agora_sp.weekday() < 5) and (agora_sp.strftime("%Y-%m-%d") not in FERIADOS_B3_2026)'
)

with open('src/monitor_realtime.py', 'w') as f:
    f.write(content)
