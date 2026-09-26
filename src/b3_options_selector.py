import datetime
import numpy as np
import pandas as pd
from scipy.stats import norm

from src.options_backtest import black_scholes_call, black_scholes_put

# Mapeamento oficial de letras de vencimento mensal da B3
LETRAS_CALL = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L'}
LETRAS_PUT  = {1: 'M', 2: 'N', 3: 'O', 4: 'P', 5: 'Q', 6: 'R', 7: 'S', 8: 'T', 9: 'U', 10: 'V', 11: 'W', 12: 'X'}


def calcular_terceira_sexta(ano: int, mes: int) -> datetime.date:
    """Calcula a data exata da 3ª sexta-feira do mês (regra oficial de vencimento da B3)."""
    # Encontra a primeira sexta-feira
    primeiro_dia = datetime.date(ano, mes, 1)
    dias_ate_sexta = (4 - primeiro_dia.weekday()) % 7
    primeira_sexta = primeiro_dia + datetime.timedelta(days=dias_ate_sexta)
    # A terceira sexta é 14 dias (2 semanas) após a primeira
    return primeira_sexta + datetime.timedelta(days=14)


def obter_vencimento_mensal_alvo(data_base: datetime.date = None):
    """
    Retorna o vencimento mensal seguro (entre 10 e 35 dias úteis).
    Se o vencimento do mês atual estiver a menos de 7 dias úteis, rola para o mês seguinte.
    """
    if data_base is None:
        data_base = datetime.date.today()

    vencimento_atual = calcular_terceira_sexta(data_base.year, data_base.month)
    dias_corridos = (vencimento_atual - data_base).days

    # Se faltar menos de 8 dias corridos para o vencimento atual, rola para o próximo mês
    if dias_corridos < 8:
        mes_seguinte = data_base.month + 1 if data_base.month < 12 else 1
        ano_seguinte = data_base.year if data_base.month < 12 else data_base.year + 1
        vencimento_alvo = calcular_terceira_sexta(ano_seguinte, mes_seguinte)
    else:
        vencimento_alvo = vencimento_atual

    dias_uteis = int(np.busday_count(data_base, vencimento_alvo))
    dias_uteis = max(dias_uteis, 1)
    return vencimento_alvo, dias_uteis


def calcular_delta_call(S, K, T, r, sigma):
    """Calcula o Delta teórico de uma Call."""
    if T <= 0:
        return 1.0 if S > K else 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1)


def calcular_delta_put(S, K, T, r, sigma):
    """Calcula o Delta teórico de uma Put."""
    if T <= 0:
        return -1.0 if S < K else 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1) - 1.0


def gerar_grade_5_strikes(ticker: str, preco_atual: float, volatilidade: float, tipo: str = 'CALL', taxa_juros: float = 0.105):
    """
    Gera a grade de 5 strikes ao redor do preço atual com o ticker oficial da B3.
    """
    vencimento, dias_uteis = obter_vencimento_mensal_alvo()
    mes_venc = vencimento.month
    T_anos = dias_uteis / 252.0

    # 4 letras base do ativo (ex: PETR, VALE, CSAN)
    raiz = ticker.replace(".SA", "")[:4]
    letra = LETRAS_CALL[mes_venc] if tipo == 'CALL' else LETRAS_PUT[mes_venc]

    # Variações percentuais dos 5 strikes (-4%, -2%, 0% [ATM], +2%, +4%)
    percentuais = [-0.04, -0.02, 0.0, 0.02, 0.04]
    grade = []

    for pct in percentuais:
        strike = round(preco_atual * (1 + pct), 2)
        distancia = ((strike - preco_atual) / preco_atual) * 100

        # Formatação do código da B3 (ex: PETRJ420 ou CSANV115)
        strike_num = int(strike * 10) if strike < 100 else int(strike)
        codigo_opcao = f"{raiz}{letra}{strike_num}"

        if tipo == 'CALL':
            premio = black_scholes_call(preco_atual, strike, T_anos, taxa_juros, volatilidade)
            delta = calcular_delta_call(preco_atual, strike, T_anos, taxa_juros, volatilidade)
            if pct < -0.01:
                moneyness = "ITM (Dentro)"
            elif abs(pct) <= 0.01:
                moneyness = "ATM (No Dinheiro)"
            else:
                moneyness = "OTM (Fora)"
        else:
            premio = black_scholes_put(preco_atual, strike, T_anos, taxa_juros, volatilidade)
            delta = calcular_delta_put(preco_atual, strike, T_anos, taxa_juros, volatilidade)
            if pct > 0.01:
                moneyness = "ITM (Dentro)"
            elif abs(pct) <= 0.01:
                moneyness = "ATM (No Dinheiro)"
            else:
                moneyness = "OTM (Fora)"

        alvo_saida_150 = premio * 2.50  # Retorno de +150%

        grade.append({
            "Código B3": codigo_opcao,
            "Tipo": tipo,
            "Strike": strike,
            "Distância (%)": round(distancia, 1),
            "Moneyness": moneyness,
            "Delta": round(delta, 2),
            "Prêmio Est.": round(premio, 2),
            "Alvo (+150%)": round(alvo_saida_150, 2),
            "Vencimento": vencimento.strftime("%d/%m/%Y"),
            "DTE (Dias Úteis)": dias_uteis,
            "_abs_delta_diff": abs(abs(delta) - 0.45)
        })

    df_grade = pd.DataFrame(grade)
    
    # Identifica a opção mais próxima do Delta 0.45 (Sweet Spot)
    idx_recomendada = df_grade['_abs_delta_diff'].idxmin()
    df_grade['Destaque'] = ""
    df_grade.loc[idx_recomendada, 'Destaque'] = "⭐ RECOMENDADA"
    
    df_grade = df_grade.drop(columns=['_abs_delta_diff'])
    return df_grade, vencimento, dias_uteis