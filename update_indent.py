with open('src/black_scholes_engine.py', 'r') as f:
    content = f.read()

content = content.replace("                if passo_strike is None:", "        if passo_strike is None:")

with open('src/black_scholes_engine.py', 'w') as f:
    f.write(content)
