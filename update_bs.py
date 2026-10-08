import re

with open('src/black_scholes_engine.py', 'r') as f:
    content = f.read()

holidays = """
FERIADOS_B3_2026 = [
    '2026-01-01', '2026-02-16', '2026-02-17', '2026-04-03', '2026-04-21',
    '2026-05-01', '2026-06-04', '2026-09-07', '2026-10-12', '2026-11-02',
    '2026-11-15', '2026-11-20', '2026-12-25'
]
"""

content = content.replace('LETRAS_PUT  = {1: \'M\', 2: \'N\', 3: \'O\', 4: \'P\', 5: \'Q\', 6: \'R\', 7: \'S\', 8: \'T\', 9: \'U\', 10: \'V\', 11: \'W\', 12: \'X\'}',
                          'LETRAS_PUT  = {1: \'M\', 2: \'N\', 3: \'O\', 4: \'P\', 5: \'Q\', 6: \'R\', 7: \'S\', 8: \'T\', 9: \'U\', 10: \'V\', 11: \'W\', 12: \'X\'}\n' + holidays)

content = content.replace('np.busday_count(data_base, vencimento_atual)',
                          'np.busday_count(data_base, vencimento_atual, holidays=FERIADOS_B3_2026)')
content = content.replace('np.busday_count(data_base, vencimento_alvo)',
                          'np.busday_count(data_base, vencimento_alvo, holidays=FERIADOS_B3_2026)')

with open('src/black_scholes_engine.py', 'w') as f:
    f.write(content)
