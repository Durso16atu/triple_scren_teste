# -*- coding: utf-8 -*-
"""
Black-Scholes Pricing & Greeks Engine para B3
Implementação analítica de Black-Scholes-Merton, sensibilidades (Gregas),
cálculo de DTE dinâmico e grade oficial de strikes padronizados da B3.
"""

from typing import Dict, Any, Union, Optional, List, Tuple
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from scipy.stats import norm

TZ_SP = ZoneInfo("America/Sao_Paulo")

# Mapeamento oficial de letras de vencimento mensal da B3
LETRAS_CALL = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L'}
LETRAS_PUT  = {1: 'M', 2: 'N', 3: 'O', 4: 'P', 5: 'Q', 6: 'R', 7: 'S', 8: 'T', 9: 'U', 10: 'V', 11: 'W', 12: 'X'}

FERIADOS_B3_2026 = [
    '2026-01-01', '2026-02-16', '2026-02-17', '2026-04-03', '2026-04-21',
    '2026-05-01', '2026-06-04', '2026-09-07', '2026-10-12', '2026-11-02',
    '2026-11-15', '2026-11-20', '2026-12-25'
]



def strike_oficial_b3(preco_teorico: float, passo: float = 1.0) -> float:
    """
    Arredonda o preço de strike teórico para o degrau oficial da B3 (padrão R$ 1,00).
    Evita decimais fracionados espúrios como R$ 45,64.
    """
    return round(round(preco_teorico / passo) * passo, 2)


def calcular_terceira_sexta(ano: int, mes: int) -> date:
    """Calcula a data exata da 3ª sexta-feira do mês (regra oficial de vencimento da B3)."""
    primeiro_dia = date(ano, mes, 1)
    dias_ate_sexta = (4 - primeiro_dia.weekday()) % 7
    primeira_sexta = primeiro_dia + timedelta(days=dias_ate_sexta)
    return primeira_sexta + timedelta(days=14)


def obter_vencimento_mensal_alvo(
    data_base: Optional[date] = None,
    dte_minimo: int = 15
) -> Tuple[date, int]:
    """
    Retorna o vencimento mensal seguro (3ª sexta-feira) e o DTE em dias úteis.
    Se o vencimento do mês atual tiver menos que dte_minimo dias úteis (ex: 15 DU),
    rola dinamicamente para o mês seguinte (Série K: 20/11/2026).
    """
    if data_base is None:
        data_base = datetime.now(TZ_SP).date()

    vencimento_atual = calcular_terceira_sexta(data_base.year, data_base.month)
    dias_uteis_atual = int(np.busday_count(data_base, vencimento_atual, holidays=FERIADOS_B3_2026)) if vencimento_atual > data_base else 0

    if dias_uteis_atual < dte_minimo:
        mes_seguinte = data_base.month + 1 if data_base.month < 12 else 1
        ano_seguinte = data_base.year if data_base.month < 12 else data_base.year + 1
        vencimento_alvo = calcular_terceira_sexta(ano_seguinte, mes_seguinte)
    else:
        vencimento_alvo = vencimento_atual

    dias_uteis = int(np.busday_count(data_base, vencimento_alvo, holidays=FERIADOS_B3_2026))
    dias_uteis = max(dias_uteis, 1)
    return vencimento_alvo, dias_uteis


class BlackScholesEngine:
    """
    Motor analítico de precificação e cálculo de gregas para opções B3.
    """

    def __init__(self, risk_free_rate: float = 0.1075):
        """
        :param risk_free_rate: Taxa Selic/CDI vigente anualizada (padrão: 0.1075 = 10,75% a.a.)
        """
        self.risk_free_rate = float(risk_free_rate)

    @staticmethod
    def calculate_historical_volatility(
        close_prices: Union[pd.Series, np.ndarray, list],
        window: int = 21,
        annualization_factor: int = 252
    ) -> float:
        """
        Calcula a volatilidade histórica anualizada baseada em retornos logarítmicos.
        """
        if isinstance(close_prices, pd.Series):
            s = close_prices.dropna()
        else:
            s = pd.Series(close_prices).dropna()

        if len(s) <= 1:
            return 0.25

        log_returns = np.log(s / s.shift(1)).dropna()
        if len(log_returns) < 2:
            return 0.25

        effective_window = min(len(log_returns), window)
        vol_sample = log_returns.tail(effective_window)
        std = vol_sample.std(ddof=1)
        if np.isnan(std) or std <= 0:
            return 0.25

        vol_anual = float(std * np.sqrt(annualization_factor))
        return max(vol_anual, 0.05)

    def evaluate_option(
        self,
        spot: float,
        strike: float,
        dte_business_days: float,
        option_type: str,
        sigma: float
    ) -> Dict[str, Any]:
        """
        Calcula analiticamente o prêmio teórico e as sensibilidades (Gregas)
        para opções de CALL ou PUT na base 252 dias úteis.
        """
        opt_type = option_type.upper().strip()
        if opt_type not in ("CALL", "PUT"):
            raise ValueError(f"option_type inválido: {option_type}. Esperado 'CALL' ou 'PUT'.")

        S = float(spot)
        K = float(strike)
        r = float(self.risk_free_rate)
        sigma = float(sigma)
        dte = float(dte_business_days)

        T = max(dte / 252.0, 1e-6)

        if T <= 1e-6:
            if opt_type == "CALL":
                intrinsic = max(0.0, S - K)
                delta = 1.0 if S > K else (0.5 if S == K else 0.0)
            else:
                intrinsic = max(0.0, K - S)
                delta = -1.0 if S < K else (-0.5 if S == K else 0.0)

            return {
                "spot": S,
                "strike": K,
                "dte_business_days": dte,
                "option_type": opt_type,
                "sigma": sigma,
                "risk_free_rate": r,
                "theoretical_price": intrinsic,
                "delta": delta,
                "gamma": 0.0,
                "vega": 0.0,
                "theta_daily": 0.0,
                "theta_pct": 0.0
            }

        sqrt_T = np.sqrt(T)
        d1 = (np.log(S / K) + (r + 0.5 * (sigma ** 2)) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        pdf_d1 = norm.pdf(d1)
        cdf_d1 = norm.cdf(d1)
        cdf_d2 = norm.cdf(d2)
        cdf_neg_d1 = norm.cdf(-d1)
        cdf_neg_d2 = norm.cdf(-d2)
        exp_discount = np.exp(-r * T)

        gamma = pdf_d1 / (S * sigma * sqrt_T)
        vega = S * pdf_d1 * sqrt_T

        if opt_type == "CALL":
            theoretical_price = S * cdf_d1 - K * exp_discount * cdf_d2
            delta = cdf_d1
            theta_annual = -(S * pdf_d1 * sigma) / (2.0 * sqrt_T) - r * K * exp_discount * cdf_d2
        else:
            theoretical_price = K * exp_discount * cdf_neg_d2 - S * cdf_neg_d1
            delta = -cdf_neg_d1
            theta_annual = -(S * pdf_d1 * sigma) / (2.0 * sqrt_T) + r * K * exp_discount * cdf_neg_d2

        theoretical_price = max(0.0, float(theoretical_price))
        theta_daily = float(theta_annual / 252.0)
        theta_pct = float(theta_daily / theoretical_price) if theoretical_price > 1e-6 else 0.0

        return {
            "spot": S,
            "strike": K,
            "dte_business_days": dte,
            "option_type": opt_type,
            "sigma": sigma,
            "risk_free_rate": r,
            "theoretical_price": theoretical_price,
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta_daily": theta_daily,
            "theta_pct": theta_pct
        }

    def gerar_grade_5_strikes(
        self,
        ticker: str,
        spot: float,
        sigma: float,
        tipo: str = "CALL",
        passo_strike: Optional[float] = None,
        data_base: Optional[date] = None
    ) -> Tuple[pd.DataFrame, date, int]:
        """
        Gera a grade oficial de 5 strikes (-6% ITM, -3% ITM, ATM, +3% OTM, +6% OTM)
        com strikes arredondados pela grade B3 e prêmios/gregas recalculados via Black-Scholes.
        """
        if passo_strike is None:
            if spot < 20.0:
                passo_strike = 0.50
            elif spot <= 50.0:
                passo_strike = 1.00
            else:
                passo_strike = 2.00
        vencimento, dias_uteis = obter_vencimento_mensal_alvo(data_base)
        mes_venc = vencimento.month
        raiz = ticker.replace(".SA", "")[:4]
        tabela = LETRAS_CALL if tipo.upper() == "CALL" else LETRAS_PUT
        letra = tabela.get(mes_venc, 'K' if tipo.upper() == "CALL" else 'W')

        if tipo.upper() == "CALL":
            degraus = [(-0.06, "ITM (Dentro)"), (-0.03, "ITM (Dentro)"), (0.00,  "ATM (No Dinheiro)"), (0.03,  "OTM (Fora)"), (0.06,  "OTM (Fora)")]
        else:
            degraus = [(0.06,  "ITM (Dentro)"), (0.03,  "ITM (Dentro)"), (0.00,  "ATM (No Dinheiro)"), (-0.03, "OTM (Fora)"), (-0.06, "OTM (Fora)")]

        strikes_iniciais = [strike_oficial_b3(spot * (1.0 + off), passo=passo_strike) for off, _ in degraus]

        if len(set(strikes_iniciais)) < len(strikes_iniciais):
            atm_s = strike_oficial_b3(spot, passo=passo_strike)
            if tipo.upper() == "CALL":
                strikes_finais = [atm_s - 2*passo_strike, atm_s - passo_strike, atm_s, atm_s + passo_strike, atm_s + 2*passo_strike]
            else:
                strikes_finais = [atm_s + 2*passo_strike, atm_s + passo_strike, atm_s, atm_s - passo_strike, atm_s - 2*passo_strike]
        else:
            strikes_finais = strikes_iniciais

        grade = []
        for strike, (offset, moneyness_label) in zip(strikes_finais, degraus):
            distancia = ((strike - spot) / spot) * 100.0
            
            if strike.is_integer():
                codigo_opcao = f"{raiz}{letra}{int(strike)}"
            else:
                codigo_opcao = f"{raiz}{letra}{str(strike).replace('.', ',')}"

            greeks = self.evaluate_option(spot=spot, strike=strike, dte_business_days=dias_uteis, option_type=tipo, sigma=sigma)
            premio_estimado = round(greeks["theoretical_price"], 2)
            alvo_150 = round(premio_estimado * 2.5, 2)
            delta = round(greeks["delta"], 2)
            gamma = round(greeks["gamma"], 4)
            theta_diario = round(greeks["theta_daily"], 4)

            grade.append({
                "Destaque": "",
                "Código B3": codigo_opcao,
                "Tipo": tipo.upper(),
                "Strike": strike,
                "Distância (%)": round(distancia, 1),
                "Moneyness": moneyness_label,
                "Delta": delta,
                "Gamma": gamma,
                "Theta": theta_diario,
                "Prêmio Est.": premio_estimado,
                "Alvo (+150%)": alvo_150,
                "Vencimento": vencimento.strftime("%d/%m/%Y"),
                "DTE (Dias Úteis)": dias_uteis
            })

        idx_recomendado, menor_distancia = -1, 999.0
        for i, item in enumerate(grade):
            abs_delta = abs(item["Delta"])
            if 0.30 <= abs_delta <= 0.45:
                dist = abs(abs_delta - 0.375)
                if dist < menor_distancia: menor_distancia, idx_recomendado = dist, i
        
        if idx_recomendado == -1:
            for i, item in enumerate(grade):
                dist = abs(abs(item["Delta"]) - 0.375)
                if dist < menor_distancia: menor_distancia, idx_recomendado = dist, i
                    
        if idx_recomendado != -1: grade[idx_recomendado]["Destaque"] = "⭐ RECOMENDADA"

        return pd.DataFrame(grade), vencimento, dias_uteis
