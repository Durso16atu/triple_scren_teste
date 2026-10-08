import re

with open('src/black_scholes_engine.py', 'r') as f:
    content = f.read()

# Update method signature
content = content.replace(
    'passo_strike: float = 1.0,',
    'passo_strike: Optional[float] = None,'
)

# Insert the dynamic passo logic
dynamic_passo = """        if passo_strike is None:
            if spot < 20.0:
                passo_strike = 0.50
            elif spot <= 50.0:
                passo_strike = 1.00
            else:
                passo_strike = 2.00"""

content = content.replace(
    'vencimento, dias_uteis = obter_vencimento_mensal_alvo(data_base)',
    dynamic_passo + '\n        vencimento, dias_uteis = obter_vencimento_mensal_alvo(data_base)'
)

with open('src/black_scholes_engine.py', 'w') as f:
    f.write(content)
