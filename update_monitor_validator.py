import re

with open('src/monitor_realtime.py', 'r') as f:
    content = f.read()

# 1. Adicionar o import
import_stmt = "from src.options_market_validator import OptionsMarketValidator"
if import_stmt not in content:
    content = content.replace("from src.webhook_dispatcher import WebhookDispatcher", 
                              f"from src.webhook_dispatcher import WebhookDispatcher\n{import_stmt}")
                              
# 2. Inicializar o validador no __init__
init_stmt = "        self.webhook = WebhookDispatcher()\n        self.validator = OptionsMarketValidator(timeout_sec=3)"
content = content.replace("        self.webhook = WebhookDispatcher()", init_stmt)

# 3. Validar a grade na varredura
validacao_stmt = """                grade_teorica = df_g.to_dict(orient="records")
                grade_validada = self.validator.validar_grade(grade_teorica)
                grades_ativas[ticker] = grade_validada"""

content = content.replace("grades_ativas[ticker] = df_g.to_dict(orient=\"records\")", validacao_stmt)

with open('src/monitor_realtime.py', 'w') as f:
    f.write(content)
